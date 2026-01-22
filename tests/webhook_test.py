import httpx
import asyncio
import os
import uuid
from fastapi import FastAPI, Request
import uvicorn
from multiprocessing import Process
import time

# Konfigürasyon
BASE_URL = "http://localhost:8000"
LISTENER_PORT = 9999
# Docker içinden Windows hosta erişim adresi
WEBHOOK_URL = f"http://host.docker.internal:{LISTENER_PORT}/webhook-receiver"

# Webhook verilerini toplamak için global bir liste (Process-safe olması için dosyaya yazacağız)
LOG_FILE = "webhook_test_log.json"

# --- Webhook Alıcı Sunucu (Ayrı Process'te çalışacak) ---
receiver_app = FastAPI()

@receiver_app.post("/webhook-receiver")
async def receive_webhook(request: Request):
    data = await request.json()
    print(f"\n[RECEIVER] Webhook alındı! Event: {data.get('event')}")
    with open(LOG_FILE, "a") as f:
        import json
        f.write(json.dumps(data) + "\n")
    return {"status": "received"}

def run_receiver():
    uvicorn.run(receiver_app, host="0.0.0.0", port=LISTENER_PORT, log_level="error")

# --- Test Ana Mantığı ---
async def run_webhook_test():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("=== WEBHOOK TEST SENARYOSU BAŞLIYOR ===")

        # 1. Kullanıcı Oluştur ve Giriş Yap
        email = f"webhook_test_{uuid.uuid4().hex[:6]}@example.com"
        password = "testpassword123"
        print(f"1. Kullanıcı kaydı: {email}")
        await client.post(f"{BASE_URL}/auth/register", json={
            "email": email, "password": password, "username": f"user_{uuid.uuid4().hex[:6]}"
        })
        login_resp = await client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Webhook Oluştur
        print(f"2. Webhook kaydediliyor: {WEBHOOK_URL}")
        wh_resp = await client.post(f"{BASE_URL}/webhooks", headers=headers, json={
            "url": WEBHOOK_URL,
            "on_success": True,
            "on_failure": True
        })
        if wh_resp.status_code not in [200, 201]:
            print(f"HATA: Webhook oluşturulamadı: {wh_resp.text}")
            return
        
        # 3. Fatura Yükle (Trigger Webhook)
        print("3. Fatura yükleniyor (Webhook tetiklenmesi için)...")
        sample_path = r"c:\Users\emreq\Desktop\Task-AI\samples\Black and White Simple Clean Mono Typed Freelancer Invoice.pdf"
        with open(sample_path, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            upload_resp = await client.post(f"{BASE_URL}/upload", headers=headers, files=files)
        
        task_id = upload_resp.json()["task_id"]
        print(f"Task ID: {task_id}. Analiz bekleniyor...")

        # 4. Polling (Analiz bitene kadar bekle)
        for i in range(30):
            status_resp = await client.get(f"{BASE_URL}/status/{task_id}", headers=headers)
            status = status_resp.json().get("status")
            print(f"   Durum: {status}...")
            if status in ["SUCCESS", "FAILED"]:
                break
            await asyncio.sleep(3)

        # 5. Webhookun Gelmesini Bekle
        print("4. Webhook çağrısı bekleniyor (max 20sn)...")
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
            print("✓ BAŞARILI: Webhook ulaştı!")
            print(f"Olay: {webhook_data.get('event')}")
            invoice_info = webhook_data.get('invoice', {})
            print(f"Fatura No: {invoice_info.get('invoice_number')}")
            print(f"Tedarikçi: {invoice_info.get('supplier_name')}")
            print("="*30)
        else:
            print("\n" + "X"*30)
            print("HATA: Webhook ulaşmadı!")
            print("İpucu: Docker container 'host.docker.internal' üzerinden Windows'a erişebiliyor mu kontrol edin.")
            print("X"*30)

        # 6. Webhook /test Endpointini Dene
        print("\n5. Webhook manuel test endpointi deneniyor...")
        wh_id = wh_resp.json()["id"]
        test_wh_resp = await client.post(f"{BASE_URL}/webhooks/{wh_id}/test", headers=headers)
        if test_wh_resp.status_code == 200:
            print("✓ Webhook test çağrısı başarılı.")
        else:
            print(f"X Webhook test çağrısı başarısız: {test_wh_resp.text}")

if __name__ == "__main__":
    # Webhook alıcısını başlat
    p = Process(target=run_receiver)
    p.start()
    
    # Küçük bir bekleme (sunucunun ayağa kalkması için)
    time.sleep(2)
    
    try:
        asyncio.run(run_webhook_test())
    finally:
        p.terminate()
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
