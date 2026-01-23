# Observability

This document lists recommended Celery queue/worker metrics and Prometheus integration.

## Target Metrics

### Queue and Worker
- `celery_workers_up` (gauge)
- `celery_queue_length` (gauge)
- `celery_task_latency_seconds` (histogram)
- `celery_task_retries_total` (counter)
- `celery_task_failures_total` (counter)

### API
- `invoice_api_requests_total`
- `invoice_processing_time_seconds`

## Prometheus Integration (Suggested)

- Use a Celery exporter or app-level metric registration.
- Add a scrape target to `prometheus.yml`.

### Example Scrape Target

```yaml
scrape_configs:
  - job_name: "celery"
    static_configs:
      - targets: ["worker:8002"]
```

## Dashboard Ideas

- Throughput and error rates
- Queue length and wait time
- Worker capacity and retry trend
