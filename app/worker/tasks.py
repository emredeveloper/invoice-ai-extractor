import os
from celery import Celery
from app.core.extraction_engine import ExtractionEngine, GeminiProvider, LocalLLMProvider
from app.core.validators import validate_arithmetic, validate_tax
import asyncio
from dotenv import load_dotenv

load_dotenv()

celery = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

def get_engine():
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider_type == "gemini":
        provider = GeminiProvider(os.getenv("GOOGLE_API_KEY"))
    else:
        provider = LocalLLMProvider(
            os.getenv("LOCAL_LLM_URL", "http://host.docker.internal:1234/v1"),
            os.getenv("LOCAL_LLM_MODEL", "qwen/qwen3-vl-4b")
        )
    return ExtractionEngine(provider)

async def _process_invoice_async(file_path: str, content_type: str):
    """Internal async helper to run the extraction and validation."""
    engine = get_engine()
    
    result = await engine.process_invoice(file_path, content_type)
    
    # Run validations (Bonus)
    result = validate_arithmetic(result)
    result = validate_tax(result)
    
    return result

@celery.task(name="tasks.process_invoice_task")
def process_invoice_task(file_path: str, content_type: str):
    try:
        # asyncio.run creates a new event loop and closes it at the end.
        # This is the standard way to run async code from a sync environment.
        return asyncio.run(_process_invoice_async(file_path, content_type))
    except Exception as e:
        # Log error for better debugging in worker logs
        import traceback
        print(f"Error processing invoice: {str(e)}")
        traceback.print_exc()
        raise e
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
