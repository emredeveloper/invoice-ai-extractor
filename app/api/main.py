import os
import asyncio
import shutil
import uuid
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, Response

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.database.connection import connect_to_mongo, close_mongo_connection, get_invoices_collection
from app.database.models import generate_id
from app.worker.tasks import celery, _process_invoice_async, DISABLE_CELERY
from app.auth.router import router as auth_router
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.api.invoices import router as invoices_router
from app.api.webhooks import router as webhooks_router
from app.api.batch import router as batch_router
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.core.metrics import MetricsMiddleware, get_metrics, metrics_content_type
from datetime import datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for MongoDB."""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="Invoice AI Extraction System (MongoDB Edition)",
    description="""
    🧾 AI-Powered Invoice Data Extraction API with MongoDB Support
    """,
    version="2.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Metrics middleware
app.add_middleware(MetricsMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(invoices_router)
app.include_router(webhooks_router)
app.include_router(batch_router)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

LOCAL_TASKS = {}
LOCAL_TASK_TIMEOUT_SECONDS = int(os.getenv("LOCAL_TASK_TIMEOUT_SECONDS", "180"))


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health_check():
    """Verify system health by checking external connections."""
    health = {"status": "healthy", "checks": {}}
    
    # Check MongoDB
    try:
        from app.database.connection import get_database
        db_instance = get_database()
        if db_instance is not None:
            await db_instance.command("ping")
            health["checks"]["mongodb"] = "ok"
        else:
            health["checks"]["mongodb"] = "not initialized"
            health["status"] = "degraded"
    except Exception as e:
        health["checks"]["mongodb"] = str(e)
        health["status"] = "unhealthy"
        
    # Check Redis/Celery
    if DISABLE_CELERY:
        health["checks"]["redis"] = "disabled"
    else:
        try:
            celery.control.ping(timeout=0.5)
            health["checks"]["redis"] = "ok"
        except Exception as e:
            health["checks"]["redis"] = str(e)
            if health["status"] == "healthy": health["status"] = "degraded"

    return health


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=get_metrics(),
        media_type=metrics_content_type()
    )


@app.post("/upload", response_model=Dict[str, str])
@limiter.limit("10/minute")
async def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a single invoice for processing with MongoDB tracking."""
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".txt"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create invoice record in MongoDB
    invoice_id = generate_id()
    invoice_doc = {
        "_id": invoice_id,
        "user_id": current_user["id"],
        "original_filename": file.filename,
        "file_type": file_ext,
        "file_size": os.path.getsize(file_path),
        "file_path": file_path,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    invoices = get_invoices_collection()
    await invoices.insert_one(invoice_doc)
    
    if DISABLE_CELERY:
        task_id = str(uuid.uuid4())
        await invoices.update_one({"_id": invoice_id}, {"$set": {"task_id": task_id}})
        LOCAL_TASKS[task_id] = {"status": "PENDING", "result": None}

        async def run_local_task():
            try:
                LOCAL_TASKS[task_id]["status"] = "STARTED"
                result = await asyncio.wait_for(
                    _process_invoice_async(file_path, file.content_type, invoice_id, current_user["id"]),
                    timeout=LOCAL_TASK_TIMEOUT_SECONDS,
                )
                LOCAL_TASKS[task_id] = {"status": "SUCCESS", "result": result}
            except asyncio.TimeoutError:
                LOCAL_TASKS[task_id] = {"status": "FAILED", "result": {"error": "processing_timeout"}}
            except Exception as exc:
                LOCAL_TASKS[task_id] = {"status": "FAILED", "result": {"error": str(exc)}}

        asyncio.create_task(run_local_task())
        return {"task_id": task_id, "invoice_id": invoice_id}

    # Trigger task
    task = celery.send_task(
        "tasks.process_invoice_task", 
        args=[file_path, file.content_type, invoice_id, current_user["id"]]
    )
    
    await invoices.update_one({"_id": invoice_id}, {"$set": {"task_id": task.id}})
    
    return {"task_id": task.id, "invoice_id": invoice_id}


@app.get("/files/{invoice_id}")
async def get_invoice_file(
    invoice_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Serve the original invoice file with security check."""
    invoices = get_invoices_collection()
    invoice = await invoices.find_one({
        "_id": invoice_id,
        "user_id": current_user["id"]
    })
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # We need to find the file in uploads directory. 
    # We don't store the path directly in invoice_doc currently, 
    # but we can reconstruct it if we had stored the file_id or the full path.
    # Looking at upload_invoice, we use a file_id (uuid) but we don't save it to DB.
    # FIX: I should have saved the file path to the DB.
    # For now, let's assume we can try to find it if we saved the task_id or similar.
    # Wait, I didn't save the filename used in UPLOAD_DIR to the DB.
    
    # RE-FIX: I need to update upload_invoice to save the file_path.
    
    file_path = invoice.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    return FileResponse(file_path)
@app.get("/status/{task_id}")
@limiter.limit("60/minute")
async def get_status(
    request: Request,
    task_id: str,
    current_user: dict = Depends(get_current_user_optional)
):
    """Get task status."""
    if DISABLE_CELERY:
        task = LOCAL_TASKS.get(task_id)
        if not task:
            return {"task_id": task_id, "status": "PENDING"}
        response = {"task_id": task_id, "status": task["status"]}
        if task["status"] == "FAILED":
            response["result"] = task.get("result") or {"error": "Processing failed"}
        elif task["status"] == "SUCCESS":
            response["result"] = task.get("result")
        return response

    task_result = celery.AsyncResult(task_id)
    response = {"task_id": task_id, "status": task_result.status}
    
    if task_result.ready():
        if task_result.failed():
            response["status"] = "FAILED"
            response["result"] = {"error": str(task_result.result)}
        else:
            response["result"] = task_result.result
            
    return response


# Mount static files at root AFTER all API routes
# This allows styles.css and app.js to be found at /styles.css etc.
# html=True means it will serve index.html for /
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
