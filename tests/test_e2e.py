import os
import time
import uuid
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SAMPLES_DIR = Path(os.getenv("SAMPLES_DIR", "samples"))
TEST_MONGODB_URL = os.getenv("TEST_MONGODB_URL", os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
TEST_DATABASE_NAME = os.getenv("TEST_DATABASE_NAME", "invoice_db")


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
def auth_headers(base_url):
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

    token = r.json().get("access_token")
    if not token:
        pytest.fail("Login response missing access_token")

    return {"Authorization": f"Bearer {token}"}


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


def test_mongodb_invoice_persisted(uploaded_invoice):
    client = _mongo_client()
    db = client[TEST_DATABASE_NAME]
    doc = db["invoices"].find_one({"_id": uploaded_invoice["invoice_id"]})
    client.close()

    assert doc is not None
    assert doc.get("status") == "completed"
    assert doc.get("file_path")
