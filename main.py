import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from tasks import celery
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(title="Invoice Data Extraction System")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    return {"message": "Invoice Data Extraction API is running."}

@app.post("/upload", response_model=Dict[str, str])
async def upload_invoice(file: UploadFile = File(...)):
    # Robust file type validation
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".txt"]
    allowed_mimes = ["application/pdf", "image/jpeg", "image/png", "text/plain", "application/octet-stream"]
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions and file.content_type not in allowed_mimes:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type ({file.content_type}). Supported: PDF, JPG, PNG, TXT."
        )
    
    # Save file temporarily
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or (".txt" if file.content_type == "text/plain" else "")
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Trigger asenkron task
    task = celery.send_task("tasks.process_invoice_task", args=[file_path, file.content_type])
    
    return {"task_id": task.id}

@app.get("/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: str):
    task_result = celery.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.status
    }
    
    if task_result.ready():
        if task_result.failed():
            response["status"] = "FAILED"
            response["result"] = {"error": str(task_result.result)}
        else:
            response["result"] = task_result.result
            
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
