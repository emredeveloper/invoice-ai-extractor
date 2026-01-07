from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
import httpx

from app.database.connection import get_webhooks_collection
from app.database.models import generate_id, webhook_helper
from app.auth.dependencies import get_current_user
from app.api.schemas import WebhookCreate, WebhookUpdate, WebhookResponse

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(current_user: dict = Depends(get_current_user)):
    """List all webhooks for the current user."""
    webhooks = get_webhooks_collection()
    
    cursor = webhooks.find({"user_id": current_user["id"]})
    items = [webhook_helper(doc) async for doc in cursor]
    
    return items


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new webhook."""
    webhooks = get_webhooks_collection()
    
    # Check webhook limit (max 5 per user)
    existing_count = await webhooks.count_documents({"user_id": current_user["id"]})
    if existing_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum webhook limit (5) reached."
        )
    
    webhook_doc = {
        "_id": generate_id(),
        "user_id": current_user["id"],
        "url": str(webhook_data.url),
        "secret": webhook_data.secret,
        "is_active": True,
        "on_success": webhook_data.on_success,
        "on_failure": webhook_data.on_failure,
        "total_calls": 0,
        "successful_calls": 0,
        "last_called_at": None,
        "last_status_code": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await webhooks.insert_one(webhook_doc)
    
    return webhook_helper(webhook_doc)


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific webhook."""
    webhooks = get_webhooks_collection()
    
    webhook = await webhooks.find_one({
        "_id": webhook_id,
        "user_id": current_user["id"]
    })
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return webhook_helper(webhook)


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    webhook_data: WebhookUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a webhook."""
    webhooks = get_webhooks_collection()
    
    webhook = await webhooks.find_one({
        "_id": webhook_id,
        "user_id": current_user["id"]
    })
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    update_data = {"updated_at": datetime.utcnow()}
    
    if webhook_data.url is not None:
        update_data["url"] = str(webhook_data.url)
    if webhook_data.secret is not None:
        update_data["secret"] = webhook_data.secret
    if webhook_data.is_active is not None:
        update_data["is_active"] = webhook_data.is_active
    if webhook_data.on_success is not None:
        update_data["on_success"] = webhook_data.on_success
    if webhook_data.on_failure is not None:
        update_data["on_failure"] = webhook_data.on_failure
    
    await webhooks.update_one({"_id": webhook_id}, {"$set": update_data})
    
    updated = await webhooks.find_one({"_id": webhook_id})
    return webhook_helper(updated)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a webhook."""
    webhooks = get_webhooks_collection()
    
    result = await webhooks.delete_one({
        "_id": webhook_id,
        "user_id": current_user["id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.post("/{webhook_id}/test", response_model=dict)
async def test_webhook(
    webhook_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Send a test request to the webhook."""
    webhooks = get_webhooks_collection()
    
    webhook = await webhooks.find_one({
        "_id": webhook_id,
        "user_id": current_user["id"]
    })
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    test_payload = {
        "event": "webhook.test",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "This is a test webhook call."
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook["url"],
                json=test_payload,
                timeout=10.0
            )
            
            return {
                "success": response.status_code < 300,
                "status_code": response.status_code,
                "response_body": response.text[:500] if response.text else None
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
