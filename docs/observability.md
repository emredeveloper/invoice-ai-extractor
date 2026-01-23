# Gozlemlenebilirlik (Observability)

Bu dokuman, Celery kuyrugu ve worker metriklerini Prometheus uzerinden izlemek icin onerilen yaklasimi listeler.

## Hedeflenen Metrikler

### Kuyruk ve Worker
- `celery_workers_up` (gauge)
- `celery_queue_length` (gauge)
- `celery_task_latency_seconds` (histogram)
- `celery_task_retries_total` (counter)
- `celery_task_failures_total` (counter)

### API
- `invoice_api_requests_total`
- `invoice_processing_time_seconds`

## Prometheus Entegrasyonu (Oneri)

- Celery icin bir exporter veya app icinde metrik kaydi kullanilir.
- `prometheus.yml` icinde ilgili scrape target eklenir.

### Ornek Scrape Hedefi

```yaml
scrape_configs:
  - job_name: "celery"
    static_configs:
      - targets: ["worker:8002"]
```

## Dashboard Onerileri

- Task throughput / hata oranlari
- Kuyruk uzunlugu ve bekleme suresi
- Worker kapasitesi ve retry trendi
