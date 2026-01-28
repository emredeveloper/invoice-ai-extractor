import json
import os
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SAMPLES_DIR = Path(os.getenv("SAMPLES_DIR", "samples"))
TEST_MONGODB_URL = os.getenv("TEST_MONGODB_URL", os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
TEST_DATABASE_NAME = os.getenv("TEST_DATABASE_NAME", "invoice_db")
WEBHOOK_TIMEOUT_SECONDS = int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "15"))
WEBHOOK_TEST_HOST = os.getenv("WEBHOOK_TEST_HOST")


def _check_api_available():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="session")
def base_url():
    if not _check_api_available():
        pytest.skip(f"API not reachable at {BASE_URL}. Start the service and re-run.")
    return BASE_URL


@pytest.fixture(scope="session")
def auth_tokens(base_url):
    email = f"e2e_{uuid.uuid4().hex[:6]}@example.com"
    password = "E2EPassword123!"
    username = f"e2e_{uuid.uuid4().hex[:6]}"

    r = requests.post(
        f"{base_url}/auth/register",
        json={"email": email, "password": password, "username": username},
        timeout=10,
    )
    if r.status_code not in (200, 201):
        pytest.fail(f"Register failed: {r.status_code} {r.text}")

    r = requests.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    if r.status_code != 200:
        pytest.fail(f"Login failed: {r.status_code} {r.text}")

    payload = r.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not access_token or not refresh_token:
        pytest.fail("Login response missing access_token")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "email": email,
        "password": password,
        "username": username,
    }


@pytest.fixture(scope="session")
def auth_headers(auth_tokens):
    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}


def _pick_sample_file():
    if not SAMPLES_DIR.exists():
        pytest.skip(f"Samples directory not found: {SAMPLES_DIR}")
    candidates = [
        p for p in SAMPLES_DIR.iterdir()
        if p.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
    ]
    if not candidates:
        pytest.skip("No sample files found in samples/")
    return candidates[0]


def _wait_for_task(base_url, task_id, headers, timeout_seconds=180):
    start = time.time()
    status = "PENDING"
    result = None
    while time.time() - start < timeout_seconds:
        r = requests.get(f"{base_url}/status/{task_id}", headers=headers, timeout=10)
        if r.status_code != 200:
            pytest.fail(f"Status failed: {r.status_code} {r.text}")
        payload = r.json()
        status = payload.get("status")
        result = payload.get("result")
        if status in {"SUCCESS", "FAILED"}:
            return status, result
        time.sleep(2)
    pytest.fail(f"Task {task_id} did not finish within {timeout_seconds}s (last: {status})")


def _mongo_client():
    try:
        client = MongoClient(TEST_MONGODB_URL, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        return client
    except ServerSelectionTimeoutError:
        pytest.skip(f"MongoDB not reachable at {TEST_MONGODB_URL}")


def _pick_webhook_host():
    if WEBHOOK_TEST_HOST:
        return WEBHOOK_TEST_HOST
    try:
        socket.gethostbyname("host.docker.internal")
        return "host.docker.internal"
    except OSError:
        return "127.0.0.1"


class _WebhookHandler(BaseHTTPRequestHandler):
    messages = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {"raw": body.decode("utf-8", errors="replace")}
        _WebhookHandler.messages.append({"headers": dict(self.headers), "payload": payload})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args, **kwargs):
        return


@pytest.fixture(scope="session")
def webhook_server():
    host = "0.0.0.0"
    server = HTTPServer((host, 0), _WebhookHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://{_pick_webhook_host()}:{port}"
    _WebhookHandler.messages = []
    yield {"url": url, "messages": _WebhookHandler.messages}
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="session")
def uploaded_invoice(base_url, auth_headers):
    sample = _pick_sample_file()
    with sample.open("rb") as f:
        r = requests.post(
            f"{base_url}/upload",
            headers=auth_headers,
            files={"file": f},
            timeout=30,
        )
    if r.status_code != 200:
        pytest.fail(f"Upload failed: {r.status_code} {r.text}")

    payload = r.json()
    task_id = payload.get("task_id")
    invoice_id = payload.get("invoice_id")
    if not task_id or not invoice_id:
        pytest.fail(f"Upload response missing task_id/invoice_id: {payload}")

    status, result = _wait_for_task(base_url, task_id, auth_headers)
    if status != "SUCCESS":
        error_text = str(result or "")
        transient_markers = [
            "503",
            "UNAVAILABLE",
            "overloaded",
            "quota",
            "rate limit",
            "429",
            "RESOURCE_EXHAUSTED",
            "exceeded your current quota",
        ]
        if any(marker in error_text for marker in transient_markers):
            pytest.skip(f"LLM transient failure during webhook trigger: {error_text}")
        pytest.fail(f"Task failed with status={status}, result={result}")

    return {
        "task_id": task_id,
        "invoice_id": invoice_id,
        "result": result,
    }


def test_health(base_url):
    r = requests.get(f"{base_url}/health", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "status" in body


def test_auth_me(base_url, auth_headers):
    r = requests.get(f"{base_url}/auth/me", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("email")

def test_refresh_token(base_url, auth_tokens):
    r = requests.post(
        f"{base_url}/auth/refresh",
        json={"refresh_token": auth_tokens["refresh_token"]},
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("access_token")


def test_api_key_flow(base_url, auth_headers):
    r = requests.post(f"{base_url}/auth/api-key", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    api_key = r.json().get("api_key")
    assert api_key

    r = requests.get(f"{base_url}/auth/me", headers={"X-API-Key": api_key}, timeout=10)
    assert r.status_code == 200


def test_upload_and_status(uploaded_invoice):
    assert isinstance(uploaded_invoice["result"], dict)

    processing_ms = uploaded_invoice["result"].get("processing_time_ms")
    if processing_ms is not None:
        assert processing_ms >= 0


def test_list_invoices(base_url, auth_headers):
    r = requests.get(f"{base_url}/invoices", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


def test_metrics_endpoint(base_url):
    r = requests.get(f"{base_url}/metrics", timeout=10)
    if r.status_code == 404:
        pytest.skip("/metrics not enabled")
    assert r.status_code == 200
    assert "invoice_api_requests_total" in r.text or "# HELP" in r.text


def test_invoice_detail_and_file_download(base_url, auth_headers, uploaded_invoice):
    invoice_id = uploaded_invoice["invoice_id"]
    r = requests.get(f"{base_url}/invoices/{invoice_id}", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("id") == invoice_id

    r = requests.get(f"{base_url}/files/{invoice_id}", headers=auth_headers, timeout=30)
    assert r.status_code == 200
    assert len(r.content) > 0


def test_dashboard_stats(base_url, auth_headers):
    r = requests.get(f"{base_url}/invoices/stats", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "total_invoices" in data


def test_export_csv_and_excel(base_url, auth_headers, uploaded_invoice):
    invoice_id = uploaded_invoice["invoice_id"]
    r = requests.post(
        f"{base_url}/invoices/export",
        headers=auth_headers,
        json={"format": "csv", "invoice_ids": [invoice_id]},
        timeout=30,
    )
    assert r.status_code == 200
    assert "Invoice No" in r.text or "Invoice No" in r.text

    r = requests.post(
        f"{base_url}/invoices/export",
        headers=auth_headers,
        json={"format": "excel", "invoice_ids": [invoice_id], "include_items": True},
        timeout=60,
    )
    assert r.status_code == 200
    assert r.headers.get("Content-Type", "").startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(r.content) > 0


def test_batch_upload_and_status(base_url, auth_headers):
    if not SAMPLES_DIR.exists():
        pytest.skip(f"Samples directory not found: {SAMPLES_DIR}")
    files = [
        p for p in SAMPLES_DIR.iterdir()
        if p.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
    ][:2]
    if len(files) < 1:
        pytest.skip("No sample files found in samples/")

    upload_files = [("files", (p.name, p.open("rb"), "application/octet-stream")) for p in files]
    try:
        r = requests.post(f"{base_url}/batch/upload", headers=auth_headers, files=upload_files, timeout=60)
    finally:
        for _, (_, fh, _) in upload_files:
            fh.close()

    assert r.status_code == 200
    payload = r.json()
    batch_id = payload.get("id")
    assert batch_id

    start = time.time()
    status = payload.get("status")
    while time.time() - start < 240:
        r = requests.get(f"{base_url}/batch/{batch_id}", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        status = data.get("status")
        if status == "completed":
            break
        time.sleep(3)
    assert status == "completed"


def test_list_batch_jobs(base_url, auth_headers):
    r = requests.get(f"{base_url}/batch", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_webhook_test_endpoint(base_url, auth_headers, webhook_server):
    webhook_server["messages"].clear()
    r = requests.post(
        f"{base_url}/webhooks",
        headers=auth_headers,
        json={"url": webhook_server["url"], "secret": "test-secret", "on_success": True, "on_failure": True},
        timeout=10,
    )
    assert r.status_code == 201
    webhook_id = r.json().get("id")
    assert webhook_id

    r = requests.post(f"{base_url}/webhooks/{webhook_id}/test", headers=auth_headers, timeout=10)
    assert r.status_code == 200

    start = time.time()
    while time.time() - start < WEBHOOK_TIMEOUT_SECONDS:
        if webhook_server["messages"]:
            break
        time.sleep(0.5)
    assert webhook_server["messages"]


def test_webhook_triggered_on_processing(base_url, auth_headers, webhook_server):
    webhook_server["messages"].clear()
    r = requests.post(
        f"{base_url}/webhooks",
        headers=auth_headers,
        json={"url": webhook_server["url"], "secret": "test-secret", "on_success": True, "on_failure": True},
        timeout=10,
    )
    assert r.status_code == 201

    sample = _pick_sample_file()
    with sample.open("rb") as f:
        r = requests.post(
            f"{base_url}/upload",
            headers=auth_headers,
            files={"file": f},
            timeout=30,
        )
    assert r.status_code == 200
    payload = r.json()
    task_id = payload.get("task_id")
    invoice_id = payload.get("invoice_id")
    assert task_id
    assert invoice_id

    status, result = _wait_for_task(base_url, task_id, auth_headers)
    if status != "SUCCESS":
        pytest.fail(f"Task failed with status={status}, result={result}")

    start = time.time()
    while time.time() - start < WEBHOOK_TIMEOUT_SECONDS:
        if webhook_server["messages"]:
            break
        time.sleep(0.5)
    assert webhook_server["messages"]


def test_mongodb_invoice_persisted(uploaded_invoice):
    client = _mongo_client()
    db = client[TEST_DATABASE_NAME]
    doc = db["invoices"].find_one({"_id": uploaded_invoice["invoice_id"]})
    client.close()

    assert doc is not None
    assert doc.get("status") == "completed"
    assert doc.get("file_path")
