# Invoice AI - Intelligent Invoice Data Extraction System

AI-powered, scalable invoice data extraction platform. Automatically extracts structured data from PDF, image, and text invoices.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

### Security and Authentication
- **JWT Authentication** - Access and refresh tokens
- **API Key** - API key for external integrations
- **Rate Limiting** - IP and user-based throttling
- **CORS** - Configurable cross-origin support

### Data Processing
- **Multi-page PDF** - Process all pages in multi-page PDFs
- **Vision AI** - Image-based OCR and extraction
- **Batch Processing** - Up to 50 invoices per batch
- **Dynamic Tax** - Supports %1, %8, %18, %20, etc.

### Integrations
- **Webhook** - HTTP callback notifications after processing
- **Export** - CSV and Excel export
- **Prometheus** - Metrics monitoring
- **Grafana** - Visual dashboards

### LLM Support
- **Google Gemini** - Cloud-based processing
- **LM Studio** - Local Qwen-VL vision model
- **Flexible Architecture** - Easy provider switching

## Quick Start

### Requirements
- Docker and Docker Compose
- (Optional) LM Studio - for local model

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/invoice-ai.git
cd invoice-ai
```

### 2. Configure Environment Variables
```bash
# Local (no Docker)
cp .env.local.example .env

# Docker
# cp .env.docker.example .env
```
Note: For local use, set `DISABLE_CELERY=true` and `DISABLE_RATE_LIMIT=true` to run without Redis (task status and rate limits are kept in memory).

### 3. Start with Docker
```bash
docker-compose up --build
```

### 4. Access Services
| Service | URL |
|--------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:8000 (or frontend folder) |
| Redis UI | http://localhost:8001 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

## API Endpoints

### Authentication
```
POST /auth/register     - Register new user
POST /auth/login        - Login (get JWT token)
POST /auth/refresh      - Refresh token
GET  /auth/me           - User info
POST /auth/api-key      - Create API key
```

### Invoice Processing
```
POST /upload            - Upload single invoice
GET  /status/{task_id}  - Check task status
POST /upload/public     - Public upload (lower limits)
```

### Invoice Management
```
GET    /invoices          - List invoices (filter, pagination)
GET    /invoices/stats    - Dashboard stats
GET    /invoices/{id}     - Invoice details
DELETE /invoices/{id}     - Delete invoice
POST   /invoices/export   - CSV/Excel export
```

### Batch Processing
```
POST /batch/upload      - Batch upload (max 50)
GET  /batch/{id}        - Batch status
GET  /batch             - Batch list
```

### Webhooks
```
GET    /webhooks           - List webhooks
POST   /webhooks           - Create webhook
GET    /webhooks/{id}      - Webhook details
PATCH  /webhooks/{id}      - Update webhook
DELETE /webhooks/{id}      - Delete webhook
POST   /webhooks/{id}/test - Test webhook
```

### Metrics
```
GET /metrics            - Prometheus metrics
GET /health             - Health check
```

Detailed examples and error schemas: [docs/api-examples.md](docs/api-examples.md)

## Configuration

### LLM Provider
```env
# Gemini (Cloud)
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_api_key

# Local (LM Studio)
LLM_PROVIDER=local
LOCAL_LLM_URL=http://localhost:1234/v1
LOCAL_LLM_MODEL=qwen/qwen3-vl-4b
```

### Rate Limiting
```env
DEFAULT_RATE_LIMIT=60/minute
UPLOAD_RATE_LIMIT=10/minute
```

### PDF Processing
```env
MAX_PDF_PAGES=10        # Max page count
PDF_DPI_SCALE=1.5       # Image quality
```

## Project Structure

```
??? app/
?   ??? api/
?   ?   ??? main.py          # FastAPI main app
?   ?   ??? invoices.py      # Invoice CRUD
?   ?   ??? webhooks.py      # Webhook management
?   ?   ??? batch.py         # Batch processing
?   ?   ??? schemas.py       # Pydantic models
?   ??? auth/
?   ?   ??? router.py        # Auth endpoints
?   ?   ??? jwt_handler.py   # JWT logic
?   ?   ??? dependencies.py  # FastAPI dependencies
?   ?   ??? schemas.py       # Auth schemas
?   ??? core/
?   ?   ??? extraction_engine.py  # LLM integration
?   ?   ??? prompts.py            # AI prompts
?   ?   ??? validators.py         # Data validation
?   ?   ??? export_service.py     # CSV/Excel export
?   ?   ??? webhook_service.py    # Webhook delivery
?   ?   ??? rate_limiter.py       # Rate limiting
?   ?   ??? metrics.py            # Prometheus metrics
?   ??? database/
?   ?   ??? connection.py    # Mongo connection
?   ?   ??? models.py        # DB models
?   ??? worker/
?       ??? tasks.py         # Celery tasks
??? frontend/
?   ??? index.html           # UI
?   ??? styles.css           # Styles
?   ??? app.js               # JS
??? tests/
??? docker-compose.yml
??? Dockerfile
??? prometheus.yml
??? requirements.txt
```

## Tests

```bash
# Run unit tests
pytest tests/

# API smoke tests
python tests/auto_test.py

# LM Studio connectivity test
python tests/lmstudio-test.py
```

Detailed testing strategy: [TESTING.md](TESTING.md)

## Metrics

### Prometheus Metrics
- `invoice_api_requests_total` - Total API requests
- `invoices_processed_total` - Total processed invoices
- `invoice_processing_time_seconds` - Processing time histogram
- `auth_attempts_total` - Auth attempts
- `webhook_calls_total` - Webhook calls

### Grafana
Default password: `admin/admin`
Prometheus data source URL: `http://prometheus:9090`

Details: [docs/observability.md](docs/observability.md)

## GDPR / KVKK Compliance

- **Automatic Deletion**: Uploaded files are deleted after processing
- **Local Processing**: With LM Studio, data stays on-prem
- **Data Minimization**: Only necessary fields are extracted
- **Audit Log**: All operations are logged
- Details: [docs/audit-log.md](docs/audit-log.md)
- Data retention policy: [docs/data-retention.md](docs/data-retention.md)

## Documentation Notes

### Post-Upload Status UX
- **Task progress visualization**: progress bar, step list, ETA.
- **Batch results table**: summary table with filters and error details.

### Audit Log Strategy
- **Format**: JSONL with `event_type`, `actor_id`, `resource_id`, `status`, `duration_ms`, `ip`, `user_agent`, `timestamp`.
- **Retention**: Default 30 days; 7/30/90/365 options.
- **Search/Filters**: Time range, event type, user, invoice id, batch id.

### KVKK/GDPR Data Retention Policy
- Automatic deletion is available; configuration options should be documented.
- Example: `RETENTION_DAYS`, `AUTO_DELETE_UPLOADS`, `PURGE_SCHEDULE`.

### Model Selection Strategy
- **Comparison**: LM Studio vs Gemini performance/accuracy/latency table.
- **Recommended scenarios**: on-prem for sensitive data, cloud for quality and speed.

### Prompt Management
- **Versioning policy**: prompt id, semver, change notes.
- **A/B testing**: traffic split, KPI tracking, outcome metrics.

### Queue Observability
- **Celery metrics**: worker count, queue length, task latency, retry count.
- **Prometheus integration**: metric names and scrape targets.

### Test Coverage and Strategy
- **Scope**: unit/API/e2e/batch/processing validation tests.
- **Test doc**: see `TESTING.md`.

### Load/Stress Testing
- **Tools**: k6 or Locust for rate limit and batch scenarios.
- **Scenarios**: 429 behavior, queue overflow, webhook latency.

### API Examples and Error Schemas
- **Examples**: single upload, batch upload, webhook test.
- **Error schema**: standard error envelope (code, message, details, request_id).

## Roadmap Priorities

1) API examples + error schemas (easier integration)
2) Test coverage and quality documentation (builds trust)
3) Observability (tracing/logging) (operational reliability)
4) LLM usage strategy and prompt versioning (quality and maintainability)

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push the branch (`git push origin feature/amazing`)
5. Open a Pull Request

## License

MIT License - See [LICENSE](LICENSE) for details.

---

QIT AI Assessment project.
