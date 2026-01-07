from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List, Optional
from datetime import datetime, timedelta

from app.database.connection import get_invoices_collection
from app.database.models import invoice_helper
from app.auth.dependencies import get_current_user
from app.api.schemas import (
    InvoiceResponse, 
    InvoiceListResponse, 
    ExportRequest,
    DashboardStats,
    InvoiceUpdate
)
from app.core.export_service import ExportService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    supplier_name: Optional[str] = None,
    invoice_number: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|total_amount|supplier_name)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: dict = Depends(get_current_user),
):
    """List invoices with filtering, pagination and sorting."""
    invoices = get_invoices_collection()
    
    # Build filter
    filter_query = {"user_id": current_user["id"]}
    
    if status:
        filter_query["status"] = status
    if supplier_name:
        filter_query["supplier_name"] = {"$regex": supplier_name, "$options": "i"}
    if invoice_number:
        filter_query["invoice_number"] = {"$regex": invoice_number, "$options": "i"}
    if date_from:
        filter_query["created_at"] = {"$gte": date_from}
    if date_to:
        if "created_at" in filter_query:
            filter_query["created_at"]["$lte"] = date_to
        else:
            filter_query["created_at"] = {"$lte": date_to}
    if min_amount is not None:
        filter_query["total_amount"] = {"$gte": min_amount}
    if max_amount is not None:
        if "total_amount" in filter_query:
            filter_query["total_amount"]["$lte"] = max_amount
        else:
            filter_query["total_amount"] = {"$lte": max_amount}
    
    # Get total count
    total = await invoices.count_documents(filter_query)
    
    # Sort direction
    sort_direction = -1 if sort_order == "desc" else 1
    
    # Pagination
    skip = (page - 1) * page_size
    
    cursor = invoices.find(filter_query).sort(sort_by, sort_direction).skip(skip).limit(page_size)
    items = [invoice_helper(doc) async for doc in cursor]
    
    total_pages = (total + page_size - 1) // page_size
    
    return InvoiceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard statistics for current user."""
    invoices = get_invoices_collection()
    user_id = current_user["id"]
    
    # Aggregation pipeline for stats
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            "pending": {"$sum": {"$cond": [{"$in": ["$status", ["pending", "processing"]]}, 1, 0]}},
            "total_amount": {"$sum": {"$ifNull": ["$total_amount", 0]}},
            "total_tax": {"$sum": {"$ifNull": ["$tax_amount", 0]}},
            "avg_processing": {"$avg": {"$ifNull": ["$processing_time_ms", 0]}},
        }}
    ]
    
    result = await invoices.aggregate(pipeline).to_list(1)
    stats = result[0] if result else {}
    
    # Time-based stats
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    
    invoices_today = await invoices.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": today_start}
    })
    
    invoices_this_week = await invoices.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": week_start}
    })
    
    # Top suppliers
    top_suppliers_pipeline = [
        {"$match": {"user_id": user_id, "supplier_name": {"$ne": None}}},
        {"$group": {
            "_id": "$supplier_name",
            "count": {"$sum": 1},
            "total": {"$sum": {"$ifNull": ["$total_amount", 0]}}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    
    top_suppliers = await invoices.aggregate(top_suppliers_pipeline).to_list(5)
    
    # Recent invoices
    recent_cursor = invoices.find({"user_id": user_id}).sort("created_at", -1).limit(5)
    recent = [invoice_helper(doc) async for doc in recent_cursor]
    
    # NEW: Spending Trend (Last 7 days)
    trend_start = today_start - timedelta(days=6)
    trend_pipeline = [
        {"$match": {
            "user_id": user_id, 
            "created_at": {"$gte": trend_start},
            "status": "completed"
        }},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "total": {"$sum": {"$ifNull": ["$total_amount", 0]}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    trend_results = await invoices.aggregate(trend_pipeline).to_list(7)
    
    # Fill gaps in trend
    spending_trend = []
    for i in range(7):
        day = (trend_start + timedelta(days=i)).strftime("%Y-%m-%d")
        day_data = next((item for item in trend_results if item["_id"] == day), None)
        spending_trend.append({
            "date": day,
            "total": day_data["total"] if day_data else 0,
            "count": day_data["count"] if day_data else 0
        })

    return DashboardStats(
        total_invoices=stats.get("total", 0),
        completed_invoices=stats.get("completed", 0),
        failed_invoices=stats.get("failed", 0),
        pending_invoices=stats.get("pending", 0),
        total_amount=stats.get("total_amount", 0),
        total_tax=stats.get("total_tax", 0),
        avg_processing_time_ms=stats.get("avg_processing", 0),
        invoices_today=invoices_today,
        invoices_this_week=invoices_this_week,
        top_suppliers=[
            {"name": s["_id"], "count": s["count"], "total": s["total"]}
            for s in top_suppliers
        ],
        recent_invoices=recent,
        spending_trend=spending_trend,
        category_stats=[
            {"name": s["_id"], "value": s["total"]}
            for s in top_suppliers
        ]
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific invoice by ID."""
    invoices = get_invoices_collection()
    
    invoice = await invoices.find_one({
        "_id": invoice_id,
        "user_id": current_user["id"]
    })
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice_helper(invoice)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    invoice_update: InvoiceUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing invoice."""
    invoices = get_invoices_collection()
    
    # Check ownership
    existing = await invoices.find_one({
        "_id": invoice_id,
        "user_id": current_user["id"]
    })
    
    if not existing:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Prepare update data
    update_data = invoice_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await invoices.update_one(
        {"_id": invoice_id},
        {"$set": update_data}
    )
    
    updated = await invoices.find_one({"_id": invoice_id})
    return invoice_helper(updated)


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete an invoice."""
    invoices = get_invoices_collection()
    
    result = await invoices.delete_one({
        "_id": invoice_id,
        "user_id": current_user["id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")


@router.post("/export")
async def export_invoices(
    export_request: ExportRequest,
    current_user: dict = Depends(get_current_user),
):
    """Export invoices to CSV or Excel."""
    invoices_col = get_invoices_collection()
    
    filter_query = {"user_id": current_user["id"]}
    
    if export_request.invoice_ids:
        filter_query["_id"] = {"$in": export_request.invoice_ids}
    if export_request.date_from:
        filter_query["created_at"] = {"$gte": export_request.date_from}
    if export_request.date_to:
        if "created_at" in filter_query:
            filter_query["created_at"]["$lte"] = export_request.date_to
        else:
            filter_query["created_at"] = {"$lte": export_request.date_to}
    
    cursor = invoices_col.find(filter_query)
    invoices = [invoice_helper(doc) async for doc in cursor]
    
    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found for export")
    
    # Convert to objects for export service
    class InvoiceObj:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
            self.items = [type('Item', (), item)() for item in data.get('items', [])]
    
    invoice_objects = [InvoiceObj(inv) for inv in invoices]
    
    if export_request.format == "csv":
        content = ExportService.export_to_csv(invoice_objects)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=invoices.csv"}
        )
    else:
        content = ExportService.export_to_excel(invoice_objects, export_request.include_items)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=invoices.xlsx"}
        )
