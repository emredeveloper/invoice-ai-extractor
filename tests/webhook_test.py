import httpx
import asyncio
import os
import uuid
from fastapi import FastAPI, Request
import uvicorn
from multiprocessing import Process
import time

# Configuration
BASE_URL = "http://localhost:8000"
LISTENER_PORT = 9999
WEBHOOK_URL = f"http://127.0.0.1:{LISTENER_PORT}/webhook-receiver"

# Persist received webhook payloads to a file (so it works across processes).
LOG_FILE = "webhook_test_log.json"

# --- Webhook receiver server (runs in a separate process) ---
receiver_app = FastAPI()

@receiver_app.post("/webhook-receiver")
async def receive_webhook(request: Request):
    data = await request.json()
    print(f"\n[RECEIVER] Webhook received! Event: {data.get('event')}")
    with open(LOG_FILE, "a") as f:
        import json
        f.write(json.dumps(data) + "\n")
    return {"status": "received"}

def run_receiver():
    uvicorn.run(receiver_app, host="0.0.0.0", port=LISTENER_PORT, log_level="error")

# --- Test main flow ---
async def run_webhook_test():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("=== WEBHOOK TEST SCENARIO START ===")

        # 1. Create user and sign in
        email = f"webhook_test_{uuid.uuid4().hex[:6]}@example.com"
        password = "testpassword123"
        print(f"1) Register user: {email}")
        await client.post(f"{BASE_URL}/auth/register", json={
            "email": email, "password": password, "username": f"user_{uuid.uuid4().hex[:6]}"
        })
        login_resp = await client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create webhook
        print(f"2) Creating webhook: {WEBHOOK_URL}")
        wh_resp = await client.post(f"{BASE_URL}/webhooks", headers=headers, json={
            "url": WEBHOOK_URL,
            "on_success": True,
            "on_failure": True
        })
        if wh_resp.status_code not in [200, 201]:
            print(f"ERROR: Failed to create webhook: {wh_resp.text}")
            return
        
        # 3. Upload invoice (triggers webhook)
        print("3) Uploading invoice (to trigger webhook)...")
        sample_path = r"c:\Users\emreq\Desktop\Task-AI\samples\Black and White Simple Clean Mono Typed Freelancer Invoice.pdf"
        with open(sample_path, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            upload_resp = await client.post(f"{BASE_URL}/upload", headers=headers, files=files)
        
        task_id = upload_resp.json()["task_id"]
        print(f"Task ID: {task_id}. Waiting for processing...")

        # 4. Poll status
        for i in range(30):
            status_resp = await client.get(f"{BASE_URL}/status/{task_id}", headers=headers)
            status = status_resp.json().get("status")
            print(f"   Status: {status}...")
            if status in ["SUCCESS", "FAILED"]:
                break
            await asyncio.sleep(3)

        # 5. Wait for webhook to arrive
        print("4) Waiting for webhook (max 20s)...")
        webhook_data = None
        for _ in range(20):
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    lines = f.readlines()
                    if lines:
                        import json
                        webhook_data = json.loads(lines[-1])
                        break
            await asyncio.sleep(1)

        if webhook_data:
            print("\n" + "="*30)
            print("✓ SUCCESS: Webhook received!")
            print(f"Event: {webhook_data.get('event')}")
            invoice_info = webhook_data.get('invoice', {})
            print(f"Invoice No: {invoice_info.get('invoice_number')}")
            print(f"Supplier: {invoice_info.get('supplier_name')}")
            print("="*30)
        else:
            print("\n" + "X"*30)
            print("ERROR: Webhook did not arrive!")
            print("X"*30)

        # 6. Call webhook /test endpoint
        print("\n5) Calling webhook test endpoint...")
        wh_id = wh_resp.json()["id"]
        test_wh_resp = await client.post(f"{BASE_URL}/webhooks/{wh_id}/test", headers=headers)
        if test_wh_resp.status_code == 200:
            print("✓ Webhook test call successful.")
        else:
            print(f"X Webhook test call failed: {test_wh_resp.text}")

if __name__ == "__main__":
    # Start webhook receiver
    p = Process(target=run_receiver)
    p.start()
    
    # Small delay to let the server start
    time.sleep(2)
    
    try:
        asyncio.run(run_webhook_test())
    finally:
        p.terminate()
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
