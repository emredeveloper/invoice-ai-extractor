from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime


# ===== Invoice Schemas =====

class InvoiceItemResponse(BaseModel):
    """Schema for invoice item response."""
    id: Optional[str] = None
    product_name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    is_arithmetic_valid: Optional[bool] = None

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    """Schema for invoice response."""
    id: str
    task_id: Optional[str] = None
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    
    # Extracted fields
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    supplier_name: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    tax_amount: Optional[float] = None
    tax_rate: Optional[float] = None
    category: Optional[str] = "General"
    
    # Validations
    arithmetic_validation: Optional[List[Dict[str, Any]]] = None
    tax_validation: Optional[Dict[str, Any]] = None
    
    # Items
    items: List[InvoiceItemResponse] = []
    
    # Agentic data
    ai_review: Optional[Dict[str, Any]] = None
    conversion: Optional[Dict[str, Any]] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InvoiceUpdate(BaseModel):
    """Schema for updating an existing invoice."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    supplier_name: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    tax_amount: Optional[float] = None
    tax_rate: Optional[float] = None
    category: Optional[str] = None
    status: Optional[str] = None


class InvoiceListResponse(BaseModel):
    """Schema for paginated invoice list."""
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class InvoiceFilter(BaseModel):
    """Schema for invoice filtering."""
    status: Optional[str] = None
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None


# ===== Webhook Schemas =====

class WebhookCreate(BaseModel):
    """Schema for creating a webhook."""
    url: HttpUrl
    secret: Optional[str] = Field(None, max_length=100)
    on_success: bool = True
    on_failure: bool = True


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""
    url: Optional[HttpUrl] = None
    secret: Optional[str] = None
    is_active: Optional[bool] = None
    on_success: Optional[bool] = None
    on_failure: Optional[bool] = None


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    id: str
    url: str
    is_active: bool
    on_success: bool
    on_failure: bool
    total_calls: int
    successful_calls: int
    last_called_at: Optional[datetime] = None
    last_status_code: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Batch Processing Schemas =====

class BatchJobResponse(BaseModel):
    """Schema for batch job response."""
    id: str
    status: str
    total_files: int
    processed_files: int
    successful_files: int
    failed_files: int
    invoice_ids: Optional[List[str]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===== Export Schemas =====

class ExportRequest(BaseModel):
    """Schema for export request."""
    format: str = Field(..., pattern="^(csv|excel)$")
    invoice_ids: Optional[List[str]] = None
    include_items: bool = True
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ===== Stats Schemas =====

class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""
    total_invoices: int
    completed_invoices: int
    failed_invoices: int
    pending_invoices: int
    total_amount: float
    total_tax: float
    avg_processing_time_ms: float
    invoices_today: int
    invoices_this_week: int
    top_suppliers: List[Dict[str, Any]]
    recent_invoices: List[InvoiceResponse]
    spending_trend: List[Dict[str, Any]] = []
    category_stats: List[Dict[str, Any]] = []
