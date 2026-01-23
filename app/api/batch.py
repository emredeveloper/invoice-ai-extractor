import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from datetime import datetime

from app.database.connection import get_invoices_collection, get_batch_jobs_collection
from app.database.models import generate_id, invoice_helper, batch_job_helper
from app.auth.dependencies import get_current_user
import asyncio
from app.worker.tasks import celery, _process_invoice_async, DISABLE_CELERY
from app.api.schemas import BatchJobResponse

router = APIRouter(prefix="/batch", tags=["Batch Processing"])

UPLOAD_DIR = "uploads"
LOCAL_TASK_TIMEOUT_SECONDS = int(os.getenv("LOCAL_TASK_TIMEOUT_SECONDS", "180"))


@router.post("/upload", response_model=BatchJobResponse)
async def batch_upload(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload multiple invoices for batch processing.
    Maximum 50 files per batch.
    """
    if len(files) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 files per batch."
        )
    
    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail="No files provided."
        )
    
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".txt"]
    
    invoices_col = get_invoices_collection()
    batch_jobs = get_batch_jobs_collection()
    
    # Create batch job
    batch_id = generate_id()
    batch_doc = {
        "_id": batch_id,
        "user_id": current_user["id"],
        "status": "processing",
        "total_files": len(files),
        "processed_files": 0,
        "successful_files": 0,
        "failed_files": 0,
        "invoice_ids": [],
        "created_at": datetime.utcnow(),
        "completed_at": None,
    }
    
    invoice_ids = []
    local_results = {"completed": 0, "failed": 0}
    
    for file in files:
        # Validate file type
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            continue
        
        # Save file
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create invoice record
        invoice_id = generate_id()
        invoice_doc = {
            "_id": invoice_id,
            "user_id": current_user["id"],
            "original_filename": file.filename,
            "file_type": ext,
            "file_size": os.path.getsize(file_path),
            "file_path": file_path,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        await invoices_col.insert_one(invoice_doc)
        invoice_ids.append(invoice_id)
        
        if DISABLE_CELERY:
            # Local mode: process synchronously to avoid background-task flakiness on Windows.
            task_id = str(uuid.uuid4())
            await invoices_col.update_one({"_id": invoice_id}, {"$set": {"task_id": task_id}})
            try:
                await asyncio.wait_for(
                    _process_invoice_async(file_path, file.content_type, invoice_id, current_user["id"]),
                    timeout=LOCAL_TASK_TIMEOUT_SECONDS,
                )
                local_results["completed"] += 1
            except asyncio.TimeoutError:
                local_results["failed"] += 1
                await invoices_col.update_one(
                    {"_id": invoice_id},
                    {"$set": {"status": "failed", "error_message": "processing_timeout", "updated_at": datetime.utcnow()}},
                )
            except Exception as exc:
                local_results["failed"] += 1
                await invoices_col.update_one(
                    {"_id": invoice_id},
                    {"$set": {"status": "failed", "error_message": str(exc), "updated_at": datetime.utcnow()}},
                )
        else:
            # Trigger async task
            task = celery.send_task(
                "tasks.process_invoice_task",
                args=[file_path, file.content_type, invoice_id, current_user["id"]]
            )

            # Update invoice with task_id
            await invoices_col.update_one(
                {"_id": invoice_id},
                {"$set": {"task_id": task.id}}
            )
    
    # Update batch job with invoice IDs
    batch_doc["invoice_ids"] = invoice_ids
    if DISABLE_CELERY:
        batch_doc["processed_files"] = local_results["completed"] + local_results["failed"]
        batch_doc["successful_files"] = local_results["completed"]
        batch_doc["failed_files"] = local_results["failed"]
        batch_doc["status"] = "completed"
        batch_doc["completed_at"] = datetime.utcnow()
    await batch_jobs.insert_one(batch_doc)
    
    return batch_job_helper(batch_doc)


@router.get("/{batch_id}", response_model=BatchJobResponse)
async def get_batch_status(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the status of a batch job."""
    batch_jobs = get_batch_jobs_collection()
    invoices_col = get_invoices_collection()
    
    batch_job = await batch_jobs.find_one({
        "_id": batch_id,
        "user_id": current_user["id"]
    })
    
    if not batch_job:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    # Update stats from invoices
    if batch_job.get("invoice_ids"):
        pipeline = [
            {"$match": {"_id": {"$in": batch_job["invoice_ids"]}}},
            {"$group": {
                "_id": None,
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            }}
        ]
        
        stats = await invoices_col.aggregate(pipeline).to_list(1)
        
        if stats:
            completed = stats[0].get("completed", 0)
            failed = stats[0].get("failed", 0)
            processed = completed + failed
            
            update_data = {
                "processed_files": processed,
                "successful_files": completed,
                "failed_files": failed,
            }
            
            if processed >= batch_job["total_files"]:
                update_data["status"] = "completed"
                update_data["completed_at"] = datetime.utcnow()
            
            await batch_jobs.update_one({"_id": batch_id}, {"$set": update_data})
            batch_job.update(update_data)
    
    return batch_job_helper(batch_job)


@router.get("", response_model=List[BatchJobResponse])
async def list_batch_jobs(current_user: dict = Depends(get_current_user)):
    """List all batch jobs for the current user."""
    batch_jobs = get_batch_jobs_collection()
    
    cursor = batch_jobs.find({"user_id": current_user["id"]}).sort("created_at", -1).limit(20)
    items = [batch_job_helper(doc) async for doc in cursor]
    
    return items
