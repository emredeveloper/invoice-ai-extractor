# GDPR/KVKK Data Retention Policy

This document explains how data retention and automatic deletion can be configured.

## Core Principles

- Uploaded files are automatically deleted after processing.
- Invoice metadata and audit logs follow the retention policy.
- Multi-tenant setups should support per-tenant retention overrides.

## Configuration (Suggested)

```env
# Retention duration (days)
RETENTION_DAYS=30

# Auto-delete uploaded files
AUTO_DELETE_UPLOADS=true

# Purge schedule (cron)
PURGE_SCHEDULE=0 3 * * *
```

## Behavior

- `RETENTION_DAYS`: How long invoice and log data are retained.
- `AUTO_DELETE_UPLOADS`: Controls post-processing file deletion.
- `PURGE_SCHEDULE`: When the cleanup job runs.

## Compliance Notes

- Field-level redaction can be applied when needed.
- Deletion events should be recorded in audit logs.
