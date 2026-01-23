import os
import sys
import time
import uuid

import requests

BASE_URL = "http://localhost:8000"
SAMPLES_DIR = "samples"

def get_auth_headers():
    """Create a user and return Authorization headers for tests."""
    email = f"auto_test_{uuid.uuid4().hex[:6]}@example.com"
    password = "TestPassword123!"
    username = f"auto_{uuid.uuid4().hex[:6]}"

    r = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password, "username": username})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Register failed: {r.status_code} {r.text}")

    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"Login failed: {r.status_code} {r.text}")

    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def run_invoice(file_path, headers):
    print(f"\n[+] Testing: {file_path}")
    
    # 1. Upload
    with open(file_path, "rb") as f:
        response = requests.post(f"{BASE_URL}/upload", headers=headers, files={"file": f})
    
    if response.status_code != 200:
        print(f"[-] Upload failed: {response.text}")
        return
    
    task_id = response.json()["task_id"]
    print(f"[*] Task ID: {task_id}. Waiting for processing...")
    
    # 2. Poll Status
    status = "PENDING"
    while status in ["PENDING", "STARTED", "RETRY"]:
        time.sleep(2)
        res = requests.get(f"{BASE_URL}/status/{task_id}", headers=headers)
        data = res.json()
        status = data["status"]
        print(f"[*] Current Status: {status}")
        
    if status == "SUCCESS":
        print("[!] SUCCESS! Extracted Data:")
        import json
        print(json.dumps(data["result"], indent=2, ensure_ascii=True))
    else:
        print(f"[-] Task failed or unexpected status: {status}")
        if "result" in data:
            print(data["result"])

if __name__ == "__main__":
    if not os.path.exists(SAMPLES_DIR):
        print(f"Error: Directory {SAMPLES_DIR} not found.")
        sys.exit(1)
        
    files = [f for f in os.listdir(SAMPLES_DIR) if f.lower().endswith(('.pdf', '.jpg', '.png', '.txt'))]
    
    if not files:
        print("No sample files found.")
        sys.exit(0)
        
    headers = get_auth_headers()
    print(f"Found {len(files)} sample files. Starting tests...")
    for file_name in files:
        run_invoice(os.path.join(SAMPLES_DIR, file_name), headers)
