# API Examples and Error Schemas

This document provides typical request/response examples and standard error schema.

## Single Invoice Upload

### Request

```bash
curl -X POST http://localhost:8000/upload   -H "Authorization: Bearer <TOKEN>"   -F "file=@invoice.pdf"
```

### Response

```json
{
  "task_id": "task_123",
  "status": "queued"
}
```

## Task Status

```bash
curl http://localhost:8000/status/task_123
```

```json
{
  "task_id": "task_123",
  "status": "completed",
  "result": {
    "invoice_number": "INV-2026-001",
    "total": 1250.75
  }
}
```

## Batch Upload

```bash
curl -X POST http://localhost:8000/batch/upload   -H "Authorization: Bearer <TOKEN>"   -F "files=@inv1.pdf"   -F "files=@inv2.pdf"
```

```json
{
  "batch_id": "batch_456",
  "status": "queued",
  "total": 2
}
```

## Standard Error Schema

```json
{
  "code": "validation_error",
  "message": "Invalid file type",
  "details": {
    "field": "file",
    "allowed": ["pdf", "png", "jpg"]
  },
  "request_id": "req_789"
}
```

## Common HTTP Codes

- `400` - validation_error
- `401` - unauthorized
- `404` - not_found
- `429` - rate_limited
- `500` - internal_error
