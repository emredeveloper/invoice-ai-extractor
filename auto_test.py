import requests
import time
import os
import sys

BASE_URL = "http://localhost:8000"
SAMPLES_DIR = "Fatura PDF"

def test_invoice(file_path):
    print(f"\n[+] Testing: {file_path}")
    
    # 1. Upload
    with open(file_path, "rb") as f:
        response = requests.post(f"{BASE_URL}/upload", files={"file": f})
    
    if response.status_code != 200:
        print(f"[-] Upload failed: {response.text}")
        return
    
    task_id = response.json()["task_id"]
    print(f"[*] Task ID: {task_id}. Waiting for processing...")
    
    # 2. Poll Status
    status = "PENDING"
    while status in ["PENDING", "STARTED", "RETRY"]:
        time.sleep(2)
        res = requests.get(f"{BASE_URL}/status/{task_id}")
        data = res.json()
        status = data["status"]
        print(f"[*] Current Status: {status}")
        
    if status == "SUCCESS":
        print("[!] SUCCESS! Extracted Data:")
        import json
        print(json.dumps(data["result"], indent=2, ensure_ascii=False))
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
        
    print(f"Found {len(files)} sample files. Starting tests...")
    for file_name in files:
        test_invoice(os.path.join(SAMPLES_DIR, file_name))
