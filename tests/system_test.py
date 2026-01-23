import asyncio
import os
import sys
import uuid

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = "http://localhost:8000"
MONGO_URL = "mongodb://localhost:27017"

TEST_USER = {
    "email": f"pro_test_{uuid.uuid4().hex[:6]}@example.com",
    "password": "ProPassword123!",
    "username": f"tester_{uuid.uuid4().hex[:6]}",
}


class Colors:
    HEADER, BLUE, GREEN, YELLOW, RED, ENDC, BOLD = (
        "\033[95m",
        "\033[94m",
        "\033[92m",
        "\033[93m",
        "\033[91m",
        "\033[0m",
        "\033[1m",
    )


def print_step(msg):
    print(f"\n{Colors.BLUE}{Colors.BOLD}>>> {msg}{Colors.ENDC}")


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.ENDC}")


def print_error(msg, detail=""):
    print(f"{Colors.RED}✗ {msg}{Colors.ENDC} {detail}")


async def run_extended_test():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f"{Colors.HEADER}{Colors.BOLD}=== INVOICE AI: EXTENDED SYSTEM TEST ==={Colors.ENDC}")

        # 1) Register and sign in
        print_step("Authentication")
        reg_resp = await client.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        if reg_resp.status_code not in (200, 201):
            print_error("Registration failed", reg_resp.text)
            return

        login_resp = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
        )
        if login_resp.status_code != 200:
            print_error("Login failed", login_resp.text)
            return

        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print_success("User created and signed in.")

        # 2) API key
        print_step("API key")
        key_resp = await client.post(f"{BASE_URL}/auth/api-key", headers=headers)
        if key_resp.status_code == 200:
            api_key = key_resp.json()["api_key"]
            print_success(f"API key created: {api_key[:10]}...")
        else:
            print_error("Failed to create API key", key_resp.text)

        # 3) Batch upload
        print_step("Batch upload")
        sample_dir = os.path.join(os.getcwd(), "samples")
        files_to_upload = [f for f in os.listdir(sample_dir) if f.lower().endswith(".pdf")][:3]

        if not files_to_upload:
            print_error("No PDF files found in samples directory!")
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
                print_error("Batch upload failed", batch_resp.text)
                return

            batch_id = batch_resp.json()["id"]
            print_success(f"Batch started. Batch ID: {batch_id} | {len(files_to_upload)} files")
        finally:
            for f in opened_files:
                f.close()

        # 4) Poll batch status
        print_step("Waiting for batch completion (polling)")
        # Local mode runs tasks in-process; timing can vary. Give it a bit more time
        # and fail explicitly if the batch does not complete.
        for i in range(60):
            b_status_resp = await client.get(f"{BASE_URL}/batch/{batch_id}", headers=headers)
            if b_status_resp.status_code != 200:
                print_error("Failed to read batch status", b_status_resp.text)
                return
            b_data = b_status_resp.json()
            sys.stdout.write(
                f"\rProcessed: {b_data['processed_files']}/{b_data['total_files']} | Status: {b_data['status']} [{i+1}/60]"
            )
            sys.stdout.flush()
            if b_data["status"] == "completed":
                break
            await asyncio.sleep(4)
        print("\n")
        if b_data.get("status") != "completed" or b_data.get("processed_files") != b_data.get("total_files"):
            print_error("Batch did not complete in time", str(b_data))
            return

        # 5) DB validation and update
        print_step("MongoDB data validation")
        try:
            db_client = AsyncIOMotorClient(MONGO_URL)
            invoices_col = db_client["invoice_db"]["invoices"]

            last_invoice = await invoices_col.find_one({"status": "completed"}, sort=[("created_at", -1)])
            if not last_invoice:
                print_error("No completed invoice found in DB!")
                return

            invoice_id = last_invoice["_id"]
            print_success(f"DB validation: invoice for '{last_invoice.get('supplier_name')}' exists.")

            print_step("Invoice update")
            update_payload = {"total_amount": 9999.99, "supplier_name": "TEST UPDATE LTD"}
            upd_resp = await client.put(f"{BASE_URL}/invoices/{invoice_id}", headers=headers, json=update_payload)
            if upd_resp.status_code == 200:
                print_success("Invoice updated successfully.")
            else:
                print_error("Update failed", upd_resp.text)

            db_client.close()
        except Exception as e:
            print_error("MongoDB connection error", str(e))

        # 6) Webhooks CRUD
        print_step("Webhooks CRUD")
        wh_data = {"url": "https://example.com/webhook", "is_active": True, "on_success": True}
        wh_resp = await client.post(f"{BASE_URL}/webhooks", headers=headers, json=wh_data)
        if wh_resp.status_code in (200, 201):
            wh_id = wh_resp.json()["id"]
            print_success(f"Webhook created: {wh_id}")
            del_resp = await client.delete(f"{BASE_URL}/webhooks/{wh_id}", headers=headers)
            if del_resp.status_code in (200, 204):
                print_success("Webhook deleted successfully.")
            else:
                print_error("Failed to delete webhook", del_resp.text)
        else:
            print_error("Failed to create webhook", wh_resp.text)

        # 7) Export (CSV)
        print_step("Export (CSV)")
        export_resp = await client.post(f"{BASE_URL}/invoices/export", headers=headers, json={"format": "csv"})
        if export_resp.status_code == 200:
            print_success(f"CSV export successful. Size: {len(export_resp.content)} bytes")
        else:
            print_error("Export failed", export_resp.text)

        # 8) Final dashboard stats
        print_step("Dashboard stats")
        stats_resp = await client.get(f"{BASE_URL}/invoices/stats", headers=headers)
        if stats_resp.status_code == 200:
            print_success(f"Final stats: {stats_resp.json()['total_invoices']} invoices in the system.")

        print(f"\n{Colors.GREEN}{Colors.BOLD}=== ALL MODULES PASSED ==={Colors.ENDC}\n")


if __name__ == "__main__":
    try:
        asyncio.run(run_extended_test())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n{Colors.RED}Critical error: {e}{Colors.ENDC}")
