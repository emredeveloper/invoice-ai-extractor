import os
import asyncio
from dotenv import load_dotenv

from celery import Celery
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.extraction_engine import ExtractionEngine, GeminiProvider, LocalLLMProvider
from app.core.validators import DataValidator
from app.core.webhook_service import WebhookService
from app.core.metrics import log_invoice_processing, ACTIVE_TASKS
from app.core.tools.exchange_rate import ExchangeRateTool
from app.core.agents.reviewer import ReviewerAgent
from app.database.connection import connect_to_mongo, get_invoices_collection

load_dotenv()

# Allow running without Redis/Celery for local dev
DISABLE_CELERY = os.getenv("DISABLE_CELERY", "false").lower() in ("1", "true", "yes")

# Eventlet monkey patch for Windows (only when Celery is enabled)
if not DISABLE_CELERY and os.name == 'nt':
    import eventlet
    eventlet.monkey_patch()

# Celery Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Fix: Docker networking hostname 'redis' doesn't work outside Docker for local terminal
if "redis://redis" in REDIS_URL and os.name == 'nt':
    REDIS_URL = REDIS_URL.replace("redis://redis", "redis://localhost")

if DISABLE_CELERY:
    print("DEBUG: Celery disabled, using in-memory broker/backend.")
    BROKER_URL = "memory://"
    BACKEND_URL = "cache+memory://"
else:
    print(f"DEBUG: Celery is connecting to: {REDIS_URL}")
    BROKER_URL = REDIS_URL
    BACKEND_URL = REDIS_URL

celery = Celery(
    "tasks",
    broker=BROKER_URL,
    backend=BACKEND_URL
)

# Configuration updates
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Istanbul',
    enable_utc=True,
    task_time_limit=300,
)

# LLM Provider Initialization
provider_type = os.getenv("LLM_PROVIDER", "gemini")
if provider_type == "gemini":
    provider = GeminiProvider(api_key=os.getenv("GOOGLE_API_KEY"))
else:
    provider = LocalLLMProvider(
        base_url=os.getenv("LOCAL_LLM_URL", "http://localhost:1234/v1"),
        model_name=os.getenv("LOCAL_LLM_MODEL", "qwen/qwen3-vl-4b")
    )

engine = ExtractionEngine(llm_provider=provider)
webhook_service = WebhookService()
exchange_tool = ExchangeRateTool()
reviewer_agent = ReviewerAgent(llm_provider=provider)

def clean_number(value: Any) -> Optional[float]:
    """Clean string number format (e.g., '1.500,00' -> 1500.0)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    
    try:
        # Remove thousands separator and fix decimal separator
        s = str(value).replace(".", "").replace(",", ".")
        # Remove any non-numeric chars except .
        import re
        s = re.sub(r'[^0-9.]', '', s)
        return float(s)
    except (ValueError, TypeError):
        return None


async def save_to_mongodb(invoice_id: str, data: Dict[str, Any], status: str, error: Optional[str] = None):
    """Save processed results to MongoDB."""
    await connect_to_mongo()  # Ensure connection
    invoices_col = get_invoices_collection()
    
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow()
    }
    
    if status == "completed":
        # Extract general fields from LLM structure
        gen_fields = data.get("general_fields", {})
        
        # Ensure items have IDs
        items = data.get("items", [])
        for item in items:
            if "id" not in item:
                import uuid
                item["id"] = str(uuid.uuid4())

        # Structure the data according to our Pydantic model
        update_data.update({
            "invoice_number": gen_fields.get("invoice_number"),
            "invoice_date": gen_fields.get("date"), # Prompt uses 'date'
            "supplier_name": gen_fields.get("supplier_name"),
            "total_amount": clean_number(gen_fields.get("total_amount")),
            "currency": gen_fields.get("currency"),
            "tax_amount": clean_number(gen_fields.get("tax_amount")),
            "tax_rate": clean_number(gen_fields.get("tax_rate")),
            "category": gen_fields.get("category", "Genel"),
            "items": [
                {
                    **item,
                    "quantity": clean_number(item.get("quantity")),
                    "unit_price": clean_number(item.get("unit_price")),
                    "total_price": clean_number(item.get("total_price"))
                } for item in items
            ],
            "arithmetic_validation": data.get("arithmetic_validation"),
            "tax_validation": data.get("tax_validation"),
            "raw_result": data.get("raw_result"),
            "processing_time_ms": data.get("processing_time_ms"),
            "ai_review": data.get("ai_review"),
            "conversion": data.get("conversion")
        })
    elif error:
        update_data["error_message"] = error
        
    await invoices_col.update_one({"_id": invoice_id}, {"$set": update_data})
    
    # Get user_id for webhook
    invoice_doc = await invoices_col.find_one({"_id": invoice_id})
    if invoice_doc:
        await webhook_service.trigger_for_invoice(invoice_doc["user_id"], invoice_doc)


async def _process_invoice_async(file_path: str, content_type: str, invoice_id: str, user_id: str):
    """Core async processing logic for MongoDB."""
    start_time = datetime.utcnow()
    ACTIVE_TASKS.inc()
    
    try:
        # 1. AI Extraction
        extraction_result = await engine.process_invoice(file_path, content_type)
        
        # Move general_fields to top-level for validators and easier access
        gen_fields = extraction_result.get("general_fields", {})
        for k, v in gen_fields.items():
            if k in ["total_amount", "tax_amount", "tax_rate"]:
                extraction_result[k] = clean_number(v)
            elif k not in extraction_result:
                extraction_result[k] = v
        
        # Clean items too
        for item in extraction_result.get("items", []):
            item["quantity"] = clean_number(item.get("quantity"))
            item["unit_price"] = clean_number(item.get("unit_price"))
            item["total_price"] = clean_number(item.get("total_price"))

        # 2. Validation
        validation_results = DataValidator.validate_invoice(extraction_result)
        extraction_result.update(validation_results)
        
        # 4. Agentic Review & Tools
        # A. Currency Conversion
        currency = extraction_result.get("currency", "TRY")
        amount = extraction_result.get("total_amount", 0)
        conversion = await exchange_tool.convert_to_try(amount, currency)
        extraction_result["conversion"] = conversion

        # B. AI Reviewer Agent
        ai_review = await reviewer_agent.review_invoice(extraction_result)
        extraction_result["ai_review"] = ai_review

        # 5. Add metadata
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        extraction_result["processing_time_ms"] = int(processing_time)
        extraction_result["raw_result"] = extraction_result.copy()
        
        # 6. Save to Database
        await save_to_mongodb(invoice_id, extraction_result, "completed")
        
        # 5. Metrics
        log_invoice_processing(
            invoice_id=invoice_id,
            status="completed",
            processing_time_ms=int(processing_time),
            llm_provider=engine.llm_provider.__class__.__name__,
            file_type=content_type
        )
        
        return extraction_result
        
    except Exception as e:
        await save_to_mongodb(invoice_id, {}, "failed", error=str(e))
        log_invoice_processing(
            invoice_id=invoice_id,
            status="failed",
            processing_time_ms=0,
            llm_provider=engine.llm_provider.__class__.__name__,
            file_type=content_type,
            error=str(e)
        )
        raise e
    finally:
        ACTIVE_TASKS.dec()
        # Cleanup file if needed (optional)
        # if os.path.exists(file_path): os.remove(file_path)


@celery.task(
    name="tasks.process_invoice_task", 
    bind=True, 
    max_retries=5,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def process_invoice_task(self, file_path: str, content_type: str, invoice_id: str, user_id: str):
    """Celery task entry point with advanced retry logic."""
    try:
        return asyncio.run(_process_invoice_async(file_path, content_type, invoice_id, user_id))
    except Exception as exc:
        # Retry on common transient errors
        error_str = str(exc).lower()
        transient_errors = ["429", "quota", "rate limit", "connection", "timeout", "resource_exhausted"]
        
        if any(err in error_str for err in transient_errors):
            raise self.retry(exc=exc)
        raise exc
