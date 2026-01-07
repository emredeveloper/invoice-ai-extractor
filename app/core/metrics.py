import os
import logging
import time
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8")
    ]
)

logger = logging.getLogger("invoice_ai")

# ===== Prometheus Metrics =====

# Counters
REQUEST_COUNT = Counter(
    'invoice_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

INVOICE_PROCESSED = Counter(
    'invoices_processed_total',
    'Total number of invoices processed',
    ['status', 'llm_provider', 'file_type']
)

AUTH_ATTEMPTS = Counter(
    'auth_attempts_total',
    'Authentication attempts',
    ['method', 'success']
)

WEBHOOK_CALLS = Counter(
    'webhook_calls_total',
    'Webhook calls made',
    ['success']
)

# Histograms
REQUEST_LATENCY = Histogram(
    'invoice_api_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

PROCESSING_TIME = Histogram(
    'invoice_processing_time_seconds',
    'Invoice processing time in seconds',
    ['llm_provider'],
    buckets=[1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# Gauges
ACTIVE_TASKS = Gauge(
    'active_processing_tasks',
    'Number of currently processing tasks'
)

QUEUE_SIZE = Gauge(
    'task_queue_size',
    'Number of tasks in queue'
)

# Info
APP_INFO = Info('invoice_ai_app', 'Application information')
APP_INFO.info({
    'version': os.getenv("APP_VERSION", "1.0.0"),
    'environment': os.getenv("ENVIRONMENT", "development")
})


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        # Calculate latency
        latency = time.time() - start_time
        
        # Get endpoint path (normalize to avoid high cardinality)
        path = request.url.path
        if path.startswith("/status/"):
            path = "/status/{task_id}"
        elif path.startswith("/invoices/"):
            path = "/invoices/{id}"
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=path,
            status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=path
        ).observe(latency)
        
        return response


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest()


def metrics_content_type() -> str:
    """Get content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST


# ===== Structured Logging Helpers =====

def log_invoice_processing(
    invoice_id: str,
    status: str,
    processing_time_ms: int,
    llm_provider: str,
    file_type: str,
    error: str = None
):
    """Log invoice processing with structured data."""
    extra = {
        "invoice_id": invoice_id,
        "status": status,
        "processing_time_ms": processing_time_ms,
        "llm_provider": llm_provider,
        "file_type": file_type
    }
    
    if status == "completed":
        logger.info(f"Invoice {invoice_id} processed successfully in {processing_time_ms}ms", extra=extra)
        INVOICE_PROCESSED.labels(status="success", llm_provider=llm_provider, file_type=file_type).inc()
        PROCESSING_TIME.labels(llm_provider=llm_provider).observe(processing_time_ms / 1000)
    else:
        extra["error"] = error
        logger.error(f"Invoice {invoice_id} processing failed: {error}", extra=extra)
        INVOICE_PROCESSED.labels(status="failure", llm_provider=llm_provider, file_type=file_type).inc()


def log_auth_attempt(method: str, success: bool, user_id: str = None, reason: str = None):
    """Log authentication attempt."""
    extra = {"method": method, "success": success}
    if user_id:
        extra["user_id"] = user_id
    if reason:
        extra["reason"] = reason
    
    if success:
        logger.info(f"Authentication successful via {method}", extra=extra)
    else:
        logger.warning(f"Authentication failed via {method}: {reason}", extra=extra)
    
    AUTH_ATTEMPTS.labels(method=method, success=str(success).lower()).inc()


def log_webhook_call(webhook_id: str, success: bool, status_code: int = None, error: str = None):
    """Log webhook call."""
    extra = {"webhook_id": webhook_id, "success": success}
    if status_code:
        extra["status_code"] = status_code
    if error:
        extra["error"] = error
    
    if success:
        logger.info(f"Webhook {webhook_id} triggered successfully", extra=extra)
    else:
        logger.error(f"Webhook {webhook_id} failed: {error}", extra=extra)
    
    WEBHOOK_CALLS.labels(success=str(success).lower()).inc()
