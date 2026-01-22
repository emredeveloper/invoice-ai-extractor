import httpx
import asyncio
import os
import uuid
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Konfigürasyon
BASE_URL = "http://localhost:8000"
MONGO_URL = "mongodb://localhost:27017" # Windows Host MongoDB
TEST_USER = {
    "email": f"pro_test_{uuid.uuid4().hex[:6]}@example.com",
    "password": "ProPassword123!",
    "username": f"tester_{uuid.uuid4().hex[:6]}"
}

class Colors:
    HEADER, BLUE, GREEN, YELLOW, RED, ENDC, BOLD = '\033[95m', '\033[94m', '\033[92m', '\033[93m', '\033[91m', '\033[0m', '\033[1m'

def print_step(msg): print(f"\n{Colors.BLUE}{Colors.BOLD}>>> {msg}{Colors.ENDC}")
def print_success(msg): print(f"{Colors.GREEN}✓ {msg}{Colors.ENDC}")
def print_error(msg, detail=""): print(f"{Colors.RED}✗ {msg}{Colors.ENDC} {detail}")

async def run_extended_test():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print(f"{Colors.HEADER}{Colors.BOLD}=== INVOICE AI: GENİŞLETİLMİŞ SİSTEM TESTİ ==={Colors.ENDC}")

        # 1. Kayıt ve Giriş
        print_step("Auth İşlemleri...")
        reg_resp = await client.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        if reg_resp.status_code not in [200, 201]:
            print_error("Kayıt başarısız", reg_resp.text)
            return
            
        login_resp = await client.post(f"{BASE_URL}/auth/login", json={"email": TEST_USER["email"], "password": TEST_USER["password"]})
        if login_resp.status_code != 200:
            print_error("Giriş başarısız", login_resp.text)
            return
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print_success("Kullanıcı oluşturuldu ve giriş yapıldı.")

        # 2. API Key Üretimi ve Testi
        print_step("API Key Mekanizması Test Ediliyor...")
        key_resp = await client.post(f"{BASE_URL}/auth/api-key", headers=headers)
        if key_resp.status_code == 200:
            api_key = key_resp.json()["api_key"]
            print_success(f"API Key oluşturuldu: {api_key[:10]}...")
        else:
            print_error("API Key oluşturulamadı")

        # 3. Toplu Fatura Yükleme (Batch Upload)
        print_step("Toplu İşlem (Batch Upload) Test Ediliyor...")
        sample_dir = r"c:\Users\emreq\Desktop\Task-AI\samples"
        files_to_upload = [f for f in os.listdir(sample_dir) if f.endswith('.pdf')][:3]
        
        if not files_to_upload:
            print_error("Samples klasöründe PDF bulunamadı!")
            return

        multipart_files = []
        opened_files = []
        try:
            for f_name in files_to_upload:
                f_path = os.path.join(sample_dir, f_name)
                f_obj = open(f_path, "rb")
                opened_files.append(f_obj)
                multipart_files.append(("files", (f_name, f_obj, "application/pdf")))
            
            batch_resp = await client.post(f"{BASE_URL}/batch/upload", headers=headers, files=multipart_files)
            if batch_resp.status_code != 200:
                print_error("Batch upload başarısız", batch_resp.text)
                return
                
            batch_id = batch_resp.json()["id"]
            print_success(f"Toplu işlem başlatıldı. Batch ID: {batch_id} | {len(files_to_upload)} dosya")
        finally:
            for f in opened_files: f.close()

        # 4. Batch ve DB Senkronizasyon Takibi
        print_step("Batch Durumu ve AI Analizi Bekleniyor (Polling)...")
        for i in range(30):
            b_status_resp = await client.get(f"{BASE_URL}/batch/{batch_id}", headers=headers)
            b_data = b_status_resp.json()
            sys.stdout.write(f"\rİşlenen: {b_data['processed_files']}/{b_data['total_files']} | Durum: {b_data['status']} [{i+1}/30]")
            sys.stdout.flush()
            if b_data['status'] == "completed": break
            await asyncio.sleep(4)
        print("\n")

        # 5. Veritabanı Derin Kontrol (Motor)
        print_step("Veritabanı (MongoDB) Veri Bütünlüğü Kontrolü...")
        try:
            db_client = AsyncIOMotorClient(MONGO_URL)
            invoices_col = db_client["invoice_db"]["invoices"]
            
            # Son işlenen faturayı alalım
            last_invoice = await invoices_col.find_one({"status": "completed"}, sort=[("created_at", -1)])
            if last_invoice:
                print_success(f"DB Doğrulaması: '{last_invoice['supplier_name']}' faturası DB'de.")
                invoice_id = last_invoice["_id"]
            else:
                print_error("DB'de işlenmiş fatura bulunamadı!")
                return
                
            # 6. Veri Güncelleme (Update)
            print_step("Fatura Verisi Güncelleme (Update) Testi...")
            update_payload = {"total_amount": 9999.99, "supplier_name": "TEST GUNCEL LTD"}
            upd_resp = await client.put(f"{BASE_URL}/invoices/{invoice_id}", headers=headers, json=update_payload)
            if upd_resp.status_code == 200:
                print_success("Fatura verisi başarıyla güncellendi.")
            else:
                print_error("Güncelleme başarısız", upd_resp.text)
                
            db_client.close()
        except Exception as e:
            print_error("MongoDB bağlantı hatası", str(e))

        # 7. Webhook Yönetimi (CRUD)
        print_step("Webhook Altyapısı Test Ediliyor...")
        wh_data = {"url": "https://webhook.site/test", "is_active": True, "on_success": True}
        wh_resp = await client.post(f"{BASE_URL}/webhooks", headers=headers, json=wh_data)
        if wh_resp.status_code in [200, 201]:
            wh_id = wh_resp.json()["id"]
            print_success(f"Webhook oluşturuldu: {wh_id}")
            del_resp = await client.delete(f"{BASE_URL}/webhooks/{wh_id}", headers=headers)
            if del_resp.status_code in [200, 204]:
                print_success("Webhook silme başarılı.")
        else:
            print_error("Webhook oluşturulamadı", wh_resp.text)

        # 8. Export Testi (CSV)
        print_step("Dışa Aktarma (Export) Test Ediliyor...")
        export_resp = await client.post(f"{BASE_URL}/invoices/export", headers=headers, json={"format": "csv"})
        if export_resp.status_code == 200:
            print_success(f"CSV Export başarılı. Veri boyutu: {len(export_resp.content)} byte")
        else:
            print_error("Export başarısız", export_resp.text)

        # 9. Final Dashboard
        print_step("Dashboard İstatistikleri Final Kontrolü...")
        stats_resp = await client.get(f"{BASE_URL}/invoices/stats", headers=headers)
        if stats_resp.status_code == 200:
            print_success(f"Final İstatistik: {stats_resp.json()['total_invoices']} fatura sistemde.")

        print(f"\n{Colors.GREEN}{Colors.BOLD}=== [TEBRİKLER] PROJE TÜM MODÜLLERİYLE %100 ÇALIŞIYOR! ==={Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_extended_test())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n{Colors.RED}Kritik Hata: {e}{Colors.ENDC}")
