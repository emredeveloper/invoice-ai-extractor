import os
import httpx
import hashlib
import hmac
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import asyncio
import logging
from app.database.connection import get_webhooks_collection

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for managing and triggering webhooks via MongoDB."""
    
    def __init__(self):
        self.timeout = float(os.getenv("WEBHOOK_TIMEOUT", "10"))
        self.max_retries = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def trigger_webhook(
        self, 
        webhook: dict, 
        event_type: str,
        invoice: dict,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "invoice": {
                "id": str(invoice["_id"]),
                "task_id": invoice.get("task_id"),
                "status": invoice.get("status"),
                "invoice_number": invoice.get("invoice_number"),
                "supplier_name": invoice.get("supplier_name"),
                "total_amount": invoice.get("total_amount"),
                "currency": invoice.get("currency"),
                "created_at": invoice.get("created_at").isoformat() if invoice.get("created_at") else None,
            }
        }
        
        if extra_data:
            payload["data"] = extra_data
        
        payload_str = json.dumps(payload)
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event_type,
            "X-Webhook-Timestamp": payload["timestamp"]
        }
        
        if webhook.get("secret"):
            signature = self._generate_signature(payload_str, webhook["secret"])
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        
        last_status = None
        webhooks_col = get_webhooks_collection()
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook["url"],
                        content=payload_str,
                        headers=headers,
                        timeout=self.timeout
                    )
                    last_status = response.status_code
                    
                    if response.status_code < 300:
                        await webhooks_col.update_one(
                            {"_id": webhook["_id"]},
                            {
                                "$inc": {"total_calls": 1, "successful_calls": 1},
                                "$set": {"last_called_at": datetime.utcnow(), "last_status_code": last_status}
                            }
                        )
                        return True
            except Exception as e:
                logger.warning(f"Webhook {webhook['_id']} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        await webhooks_col.update_one(
            {"_id": webhook["_id"]},
            {
                "$inc": {"total_calls": 1},
                "$set": {"last_called_at": datetime.utcnow(), "last_status_code": last_status}
            }
        )
        return False
    
    async def trigger_for_invoice(
        self, 
        user_id: str, 
        invoice: dict, 
        event_type: str = "invoice.processed"
    ):
        webhooks_col = get_webhooks_collection()
        cursor = webhooks_col.find({"user_id": user_id, "is_active": True})
        
        is_success = invoice.get("status") == "completed"
        is_failure = invoice.get("status") == "failed"
        
        async for webhook in cursor:
            should_trigger = (
                (is_success and webhook.get("on_success", True)) or
                (is_failure and webhook.get("on_failure", True))
            )
            if should_trigger:
                await self.trigger_webhook(webhook, event_type, invoice)
