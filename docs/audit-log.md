# Audit Log Strategy

This document defines the audit log format, retention policy, and search/filtering approach.

## Format

- Logs are stored in JSONL (one JSON per line).
- Required fields:
  - `event_type`
  - `actor_id`
  - `resource_type`
  - `resource_id`
  - `status`
  - `duration_ms`
  - `ip`
  - `user_agent`
  - `timestamp`
- Optional fields:
  - `batch_id`
  - `task_id`
  - `request_id`
  - `error_code`
  - `error_message`

### Example Record

```json
{"event_type":"invoice.process","actor_id":"user_123","resource_type":"invoice","resource_id":"inv_456","status":"success","duration_ms":842,"ip":"203.0.113.10","user_agent":"Mozilla/5.0","timestamp":"2026-01-22T21:40:12Z","task_id":"task_abc","request_id":"req_xyz"}
```

## Event Types (Suggested)

- `auth.login`
- `auth.refresh`
- `invoice.upload`
- `invoice.process`
- `invoice.export`
- `batch.upload`
- `batch.process`
- `webhook.deliver`

## Retention Policy

- Default retention: **30 days**.
- Config options: **7 / 30 / 90 / 365 days**.
- Tenant-level overrides are supported in multi-tenant setups.

## Search and Filtering

- Time range (start/end)
- `event_type`
- `actor_id`
- `resource_id`
- `batch_id` / `task_id`
- `status`

## Access and Security

- Only authorized roles can read audit logs.
- Sensitive fields (PII) should be masked or hashed.
- Logs should be stored immutably.

## Implementation Notes (Suggested)

- File-based JSONL or a DB table can be used.
- Rotation and scheduled purging should be implemented.
- Use `request_id` for correlation with API logs.
