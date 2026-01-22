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
    "email": f"agent_test_{uuid.uuid4().hex[:6]}@example.com",
    "password": "AgentPassword123!",
    "username": f"agent_tester_{uuid.uuid4().hex[:6]}"
}

class Colors:
    HEADER, BLUE, GREEN, YELLOW, RED, ENDC, BOLD = '\033[95m', '\033[94m', '\033[92m', '\033[93m', '\033[91m', '\033[0m', '\033[1m'

def print_step(msg): print(f"\n{Colors.BLUE}{Colors.BOLD}>>> {msg}{Colors.ENDC}")
def print_success(msg): print(f"{Colors.GREEN}✓ {msg}{Colors.ENDC}")
def print_error(msg, detail=""): print(f"{Colors.RED}✗ {msg}{Colors.ENDC} {detail}")

async def run_agent_test():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f"{Colors.HEADER}{Colors.BOLD}=== INVOICE AI: AGENT & TOOL TESTİ ==={Colors.ENDC}")

        # 1. Auth
        await client.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        login_resp = await client.post(f"{BASE_URL}/auth/login", json={"email": TEST_USER["email"], "password": TEST_USER["password"]})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print_success("Giriş yapıldı.")

        # 2. Fatura Yükle (USD'li bir fatura olması iyi olur)
        print_step("Fatura Yükleniyor (Agent'lar tetikleniyor)...")
        sample_path = r"c:\Users\emreq\Desktop\Task-AI\samples\Black and White Simple Clean Mono Typed Freelancer Invoice.pdf"
        with open(sample_path, "rb") as f:
            files = {"file": ("exchange_test.pdf", f, "application/pdf")}
            upload_resp = await client.post(f"{BASE_URL}/upload", headers=headers, files=files)
        
        task_id = upload_resp.json()["task_id"]
        invoice_id = upload_resp.json()["invoice_id"]
        print_success(f"Yüklendi. Task ID: {task_id}")

        # 3. Bekle (Ajanların düşünmesi biraz zaman alabilir)
        print_step("Ajanların ve Araçların Çalışması Bekleniyor...")
        for i in range(40):
            status_resp = await client.get(f"{BASE_URL}/status/{task_id}", headers=headers)
            status_data = status_resp.json()
            sys.stdout.write(f"\rDurum: {status_data['status']} [{i+1}/40]")
            sys.stdout.flush()
            if status_data['status'] == "SUCCESS":
                break
            await asyncio.sleep(3)
        print("\n")

        # 4. Veritabanı Kontrolü (Ajan çıktılarını buradan okuyacağız)
        print_step("Veritabanından Ajan Çıktıları Doğrulanıyor...")
        db_client = AsyncIOMotorClient(MONGO_URL)
        db = db_client["invoice_db"]
        doc = await db["invoices"].find_one({"_id": invoice_id})
        
        if doc:
            # A. Conversion Tool Kontrolü
            conversion = doc.get("conversion")
            if conversion:
                print_success(f"Döviz Aracı Çalıştı: {doc['total_amount']} {doc.get('currency')} -> {conversion.get('amount_try')} TRY (Kur: {conversion.get('rate')})")
            else:
                print_error("Döviz çevrim verisi bulunamadı!")

            # B. Reviewer Agent Kontrolü
            ai_review = doc.get("ai_review")
            if ai_review:
                print_success(f"İnceleme Ajanı (Reviewer) Çalıştı:")
                print(f"   {Colors.YELLOW}Özet:{Colors.ENDC} {ai_review.get('summary')}")
                print(f"   {Colors.YELLOW}Risk Seviyesi:{Colors.ENDC} {ai_review.get('risk_level')}")
                print(f"   {Colors.YELLOW}Öneri:{Colors.ENDC} {ai_review.get('suggested_action')}")
            else:
                print_error("AI Reviewer çıktısı bulunamadı!")
        else:
            print_error("Fatura DB'de bulunamadı!")
        
        db_client.close()
        print(f"\n{Colors.GREEN}{Colors.BOLD}=== AGENT & TOOL TESTİ TAMAMLANDI ==={Colors.ENDC}\n")

if __name__ == "__main__":
    asyncio.run(run_agent_test())
