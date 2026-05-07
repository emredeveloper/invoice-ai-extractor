# Invoice AI - Intelligent Invoice Data Extraction System

AI-powered, scalable invoice data extraction platform. It extracts structured data from PDF, image, and text invoices and exposes the workflow through a FastAPI backend.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

### Security and Authentication
- JWT authentication with access and refresh tokens
- API key support for external integrations
- IP and user-based rate limiting
- Configurable CORS

### Data Processing
- Multi-page PDF processing
- Vision AI based OCR and extraction
- Batch processing for up to 50 invoices
- Dynamic tax support for rates such as 1%, 8%, 18%, and 20%

### Integrations
- Webhook callback notifications after processing
- CSV and Excel export
- Prometheus metrics
- Grafana dashboard support

### LLM Support
- Google Gemini for cloud-based processing
- LM Studio for local vision model workflows
- Provider-based architecture for easier switching

## Quick Start

### Requirements

- Python 3.11+
- Docker and Docker Compose, optional
- Redis, required unless local no-queue mode is enabled
- MongoDB, required for persistent storage
- Optional: LM Studio for local model processing

### 1. Clone the Repository

```bash
git clone https://github.com/emredeveloper/invoice-ai-extractor.git
cd invoice-ai-extractor
```

### 2. Configure Environment Variables

```bash
# Local development
cp .env.local.example .env

# Docker deployment
# cp .env.docker.example .env
```

For local development without Redis, set:

```env
DISABLE_CELERY=true
DISABLE_RATE_LIMIT=true
```

In this mode, task status and rate limits are kept in memory.

### 3. Start with Docker

```bash
docker compose up --build
```

### 4. Access Services

| Service | URL |
|--------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:8000 |
| Redis UI | http://localhost:8001 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

> For demo environments, Grafana may use `admin/admin`. Change default credentials before production use.

## API Endpoints

### Authentication

```text
POST /auth/register     - Register new user
POST /auth/login        - Login and get JWT token
POST /auth/refresh      - Refresh token
GET  /auth/me           - Current user info
POST /auth/api-key      - Create API key
```

### Invoice Processing

```text
POST /upload            - Upload single invoice
GET  /status/{task_id}  - Check task status
POST /upload/public     - Public upload with lower limits
```

### Invoice Management

```text
GET    /invoices          - List invoices with filters and pagination
GET    /invoices/stats    - Dashboard stats
GET    /invoices/{id}     - Invoice details
DELETE /invoices/{id}     - Delete invoice
POST   /invoices/export   - CSV or Excel export
```

### Batch Processing

```text
POST /batch/upload      - Batch upload, max 50 files
GET  /batch/{id}        - Batch status
GET  /batch             - Batch list
```

### Webhooks

```text
GET    /webhooks           - List webhooks
POST   /webhooks           - Create webhook
GET    /webhooks/{id}      - Webhook details
PATCH  /webhooks/{id}      - Update webhook
DELETE /webhooks/{id}      - Delete webhook
POST   /webhooks/{id}/test - Test webhook
```

### Metrics

```text
GET /metrics            - Prometheus metrics
GET /health             - Health check
```

Detailed examples and error schemas: [docs/api-examples.md](docs/api-examples.md)

## Configuration

### LLM Provider

```env
# Gemini cloud provider
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_key

# Local LM Studio provider
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
MAX_PDF_PAGES=10
PDF_DPI_SCALE=1.5
```

## Project Structure

```text
invoice-ai-extractor/
├── app/
│   ├── api/
│   │   ├── main.py          # FastAPI main app
│   │   ├── invoices.py      # Invoice CRUD
│   │   ├── webhooks.py      # Webhook management
│   │   ├── batch.py         # Batch processing
│   │   └── schemas.py       # Pydantic models
│   ├── auth/
│   │   ├── router.py        # Auth endpoints
│   │   ├── jwt_handler.py   # JWT logic
│   │   ├── dependencies.py  # FastAPI dependencies
│   │   └── schemas.py       # Auth schemas
│   ├── core/
│   │   ├── extraction_engine.py
│   │   ├── prompts.py
│   │   ├── validators.py
│   │   ├── export_service.py
│   │   ├── webhook_service.py
│   │   ├── rate_limiter.py
│   │   └── metrics.py
│   ├── database/
│   │   ├── connection.py
│   │   └── models.py
│   └── worker/
│       └── tasks.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/
├── docker-compose.yml
├── Dockerfile
├── prometheus.yml
├── requirements.txt
└── README.md
```

## Tests

```bash
pytest tests/
python tests/auto_test.py
python tests/lmstudio-test.py
```

Detailed testing strategy: [TESTING.md](TESTING.md)

## Metrics

Prometheus metrics include:

- `invoice_api_requests_total`
- `invoices_processed_total`
- `invoice_processing_time_seconds`
- `auth_attempts_total`
- `webhook_calls_total`

Details: [docs/observability.md](docs/observability.md)

## GDPR / KVKK Compliance

- Uploaded files can be automatically deleted after processing
- Local processing keeps sensitive data on-prem when LM Studio is used
- Only necessary fields are extracted
- Audit logs can track user and invoice operations
- Details: [docs/audit-log.md](docs/audit-log.md)
- Data retention policy: [docs/data-retention.md](docs/data-retention.md)

## Roadmap Priorities

1. API examples and standard error schemas
2. Test coverage and quality documentation
3. Observability with tracing and structured logging
4. LLM usage strategy and prompt versioning
5. Load and stress testing with k6 or Locust

## Contributing

1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Push the branch
5. Open a pull request

## License

MIT License - See [LICENSE](LICENSE) for details.
