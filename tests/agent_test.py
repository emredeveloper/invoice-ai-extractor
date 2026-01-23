import asyncio
import os
import sys
import uuid

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = "http://localhost:8000"
MONGO_URL = "mongodb://localhost:27017"

TEST_USER = {
    "email": f"agent_test_{uuid.uuid4().hex[:6]}@example.com",
    "password": "AgentPassword123!",
    "username": f"agent_tester_{uuid.uuid4().hex[:6]}",
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


async def run_agent_test():
    async with httpx.AsyncClient(timeout=180.0) as client:
        print(f"{Colors.HEADER}{Colors.BOLD}=== INVOICE AI: AGENT & TOOL TEST ==={Colors.ENDC}")

        # 1) Auth
        await client.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        login_resp = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print_success("Signed in.")

        # 2) Upload invoice (ideally a non-TRY invoice)
        print_step("Uploading invoice (agents and tools will run)")
        sample_path = os.path.join(os.getcwd(), "samples", "Black and White Simple Clean Mono Typed Freelancer Invoice.pdf")
        with open(sample_path, "rb") as f:
            files = {"file": ("exchange_test.pdf", f, "application/pdf")}
            upload_resp = await client.post(f"{BASE_URL}/upload", headers=headers, files=files)

        if upload_resp.status_code != 200:
            print_error("Upload failed", upload_resp.text)
            return

        task_id = upload_resp.json()["task_id"]
        invoice_id = upload_resp.json()["invoice_id"]
        print_success(f"Uploaded. Task ID: {task_id}")

        # 3) Wait for completion
        print_step("Waiting for processing")
        for i in range(60):
            status_resp = await client.get(f"{BASE_URL}/status/{task_id}", headers=headers)
            status_data = status_resp.json()
            sys.stdout.write(f"\rStatus: {status_data['status']} [{i+1}/60]")
            sys.stdout.flush()
            if status_data["status"] in ("SUCCESS", "FAILED"):
                break
            await asyncio.sleep(3)
        print("\n")

        # 4) Validate agent/tool outputs from DB
        print_step("Validating agent outputs in MongoDB")
        db_client = AsyncIOMotorClient(MONGO_URL)
        db = db_client["invoice_db"]
        doc = await db["invoices"].find_one({"_id": invoice_id})

        if not doc:
            print_error("Invoice not found in DB")
            db_client.close()
            return

        conversion = doc.get("conversion")
        if conversion:
            print_success(
                f"Currency tool: {doc.get('total_amount')} {doc.get('currency')} -> {conversion.get('amount_try')} TRY (rate: {conversion.get('rate')})"
            )
        else:
            print_error("Currency conversion data not found")

        ai_review = doc.get("ai_review")
        if ai_review:
            print_success("Reviewer agent output:")
            print(f"   {Colors.YELLOW}Summary:{Colors.ENDC} {ai_review.get('summary')}")
            print(f"   {Colors.YELLOW}Risk:{Colors.ENDC} {ai_review.get('risk_level')}")
            print(f"   {Colors.YELLOW}Suggestion:{Colors.ENDC} {ai_review.get('suggested_action')}")
        else:
            print_error("Reviewer output not found")

        db_client.close()
        print(f"\n{Colors.GREEN}{Colors.BOLD}=== AGENT & TOOL TEST COMPLETE ==={Colors.ENDC}\n")


if __name__ == "__main__":
    asyncio.run(run_agent_test())

