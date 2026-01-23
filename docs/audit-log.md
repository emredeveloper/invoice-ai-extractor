# Audit Log Stratejisi

Bu dokuman, audit log formatini, saklama politikasini ve arama/filtreleme yaklasimini tanimlar.

## Format

- Loglar JSONL (her satir bir JSON kaydi) formatinda tutulur.
- Zorunlu alanlar:
  - `event_type`
  - `actor_id`
  - `resource_type`
  - `resource_id`
  - `status`
  - `duration_ms`
  - `ip`
  - `user_agent`
  - `timestamp`
- Opsiyonel alanlar:
  - `batch_id`
  - `task_id`
  - `request_id`
  - `error_code`
  - `error_message`

### Ornek Kayit

```json
{"event_type":"invoice.process","actor_id":"user_123","resource_type":"invoice","resource_id":"inv_456","status":"success","duration_ms":842,"ip":"203.0.113.10","user_agent":"Mozilla/5.0","timestamp":"2026-01-22T21:40:12Z","task_id":"task_abc","request_id":"req_xyz"}
```

## Event Tipleri (Oneri)

- `auth.login`
- `auth.refresh`
- `invoice.upload`
- `invoice.process`
- `invoice.export`
- `batch.upload`
- `batch.process`
- `webhook.deliver`

## Saklama Politikasi

- Varsayilan saklama suresi: **30 gun**.
- Konfigurasyon secenekleri: **7 / 30 / 90 / 365 gun**.
- Multeci saklama (multi-tenant) icin tenant bazli override desteklenir.

## Arama ve Filtreleme

- Zaman araligi (start/end)
- `event_type`
- `actor_id`
- `resource_id`
- `batch_id` / `task_id`
- `status`

## Eri?im ve Guvenlik

- Sadece yetkili roller audit log okuyabilir.
- Hassas alanlar (PII) maskeleme veya hash ile saklanir.
- Log kayitlari immutable olacak sekilde depolanir.

## Uygulama Notlari (Oneri)

- Dosya tabanli JSONL veya DB tablosu secilebilir.
- Log rotasyonu ve periyodik purging jobu planlanir.
- `request_id` ile API loglariyla korelasyon saglanir.
