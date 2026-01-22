import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


# ===== User Models =====

class UserInDB(BaseModel):
    """User document in MongoDB."""
    id: str = Field(default_factory=generate_id, alias="_id")
    email: EmailStr
    username: str
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    api_key: Optional[str] = None
    rate_limit_per_minute: int = 60
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ===== Invoice Models =====

class InvoiceItemInDB(BaseModel):
    """Invoice item embedded document."""
    id: str = Field(default_factory=generate_id)
    product_name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    is_arithmetic_valid: Optional[bool] = None


class InvoiceInDB(BaseModel):
    """Invoice document in MongoDB."""
    id: str = Field(default_factory=generate_id, alias="_id")
    user_id: str
    task_id: Optional[str] = None
    
    # File info
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    
    # Processing status
    status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    
    # Extracted general fields
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    supplier_name: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    tax_amount: Optional[float] = None
    tax_rate: Optional[float] = None
    
    # Raw JSON result from LLM
    raw_result: Optional[Dict[str, Any]] = None
    
    # Validation results
    arithmetic_validation: Optional[List[Dict[str, Any]]] = None
    tax_validation: Optional[Dict[str, Any]] = None
    
    # Agentic data
    ai_review: Optional[Dict[str, Any]] = None
    conversion: Optional[Dict[str, Any]] = None
    
    # Embedded items (denormalized for performance)
    items: List[InvoiceItemInDB] = []
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ===== Webhook Models =====

class WebhookInDB(BaseModel):
    """Webhook document in MongoDB."""
    id: str = Field(default_factory=generate_id, alias="_id")
    user_id: str
    
    url: str
    secret: Optional[str] = None
    is_active: bool = True
    
    # Events to trigger
    on_success: bool = True
    on_failure: bool = True
    
    # Stats
    total_calls: int = 0
    successful_calls: int = 0
    last_called_at: Optional[datetime] = None
    last_status_code: Optional[int] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ===== Batch Job Models =====

class BatchJobInDB(BaseModel):
    """Batch job document in MongoDB."""
    id: str = Field(default_factory=generate_id, alias="_id")
    user_id: str
    
    status: str = "pending"  # pending, processing, completed, failed
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    
    # Store invoice IDs in this batch
    invoice_ids: List[str] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ===== Metrics Models =====

class ProcessingMetricsInDB(BaseModel):
    """Metrics document in MongoDB."""
    id: str = Field(default_factory=generate_id, alias="_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Counters
    total_requests: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    
    # Timing
    avg_processing_time_ms: Optional[float] = None
    min_processing_time_ms: Optional[float] = None
    max_processing_time_ms: Optional[float] = None
    
    # LLM Provider stats
    llm_provider: Optional[str] = None
    llm_tokens_used: Optional[int] = None
    
    # File type breakdown
    pdf_count: int = 0
    image_count: int = 0
    text_count: int = 0

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ===== Helper Functions =====

def user_helper(user: dict) -> dict:
    """Convert MongoDB user document to response format."""
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "username": user["username"],
        "is_active": user.get("is_active", True),
        "is_admin": user.get("is_admin", False),
        "api_key": user.get("api_key"),
        "rate_limit_per_minute": user.get("rate_limit_per_minute", 60),
        "created_at": user["created_at"],
    }


def invoice_helper(invoice: dict) -> dict:
    """Convert MongoDB invoice document to response format."""
    return {
        "id": str(invoice["_id"]),
        "user_id": invoice.get("user_id"),
        "task_id": invoice.get("task_id"),
        "original_filename": invoice.get("original_filename"),
        "file_type": invoice.get("file_type"),
        "file_size": invoice.get("file_size"),
        "status": invoice.get("status", "pending"),
        "error_message": invoice.get("error_message"),
        "processing_time_ms": invoice.get("processing_time_ms"),
        "invoice_number": invoice.get("invoice_number"),
        "invoice_date": invoice.get("invoice_date"),
        "supplier_name": invoice.get("supplier_name"),
        "total_amount": invoice.get("total_amount"),
        "currency": invoice.get("currency"),
        "tax_amount": invoice.get("tax_amount"),
        "tax_rate": invoice.get("tax_rate"),
        "arithmetic_validation": invoice.get("arithmetic_validation"),
        "tax_validation": invoice.get("tax_validation"),
        "items": [
            {**item, "id": item.get("id") or str(uuid.uuid4())} 
            for item in invoice.get("items", [])
        ],
        "ai_review": invoice.get("ai_review"),
        "conversion": invoice.get("conversion"),
        "created_at": invoice.get("created_at"),
        "updated_at": invoice.get("updated_at"),
    }


def webhook_helper(webhook: dict) -> dict:
    """Convert MongoDB webhook document to response format."""
    return {
        "id": str(webhook["_id"]),
        "user_id": webhook.get("user_id"),
        "url": webhook.get("url"),
        "is_active": webhook.get("is_active", True),
        "on_success": webhook.get("on_success", True),
        "on_failure": webhook.get("on_failure", True),
        "total_calls": webhook.get("total_calls", 0),
        "successful_calls": webhook.get("successful_calls", 0),
        "last_called_at": webhook.get("last_called_at"),
        "last_status_code": webhook.get("last_status_code"),
        "created_at": webhook.get("created_at"),
    }


def batch_job_helper(job: dict) -> dict:
    """Convert MongoDB batch job document to response format."""
    return {
        "id": str(job["_id"]),
        "user_id": job.get("user_id"),
        "status": job.get("status", "pending"),
        "total_files": job.get("total_files", 0),
        "processed_files": job.get("processed_files", 0),
        "successful_files": job.get("successful_files", 0),
        "failed_files": job.get("failed_files", 0),
        "invoice_ids": job.get("invoice_ids", []),
        "created_at": job.get("created_at"),
        "completed_at": job.get("completed_at"),
    }
