# Testing Strategy and Coverage

This document summarizes test coverage and how to run the existing tests.

## Coverage

### Unit
- Unit tests for validators and processing logic (pytest).
- Focus on error scenarios and field validation.

### API and Integration
- Core API flows and upload scenarios (automation tests).
- Webhook triggers and callback validation.

### System and Agent Tests
- System test: full end-to-end flow.
- Agent test: minimum behavior validation for LLM-driven flows.

### LLM Connectivity
- LM Studio connectivity test and sample response.

## Test Files

- `tests/auto_test.py` - API upload flows (smoke/acceptance)
- `tests/webhook_test.py` - Webhook flows
- `tests/system_test.py` - End-to-end system test
- `tests/agent_test.py` - Agent/LLM behavior test
- `tests/lmstudio-test.py` - LM Studio connectivity test

## Running

```bash
# Unit tests
pytest tests/

# API smoke tests
python tests/auto_test.py

# Webhook flows
python tests/webhook_test.py

# System test
python tests/system_test.py

# Agent/LLM test
python tests/agent_test.py

# LM Studio connectivity
python tests/lmstudio-test.py

# E2E API checks (requires running API)
# Optional env: TEST_MONGODB_URL, TEST_DATABASE_NAME, WEBHOOK_TEST_HOST
pytest tests/test_e2e.py
```

## Environment Prerequisites

- Services should be running via `docker-compose up --build`.
- LLM tests require `LLM_PROVIDER` and related keys/URLs.
- Sample PDFs are in `samples/`.

## Expected Results

- API tests return HTTP 200/201 and tasks complete.
- Webhook tests hit the target endpoint successfully.
- LLM tests return a sample response.

## Coverage Gaps (Backlog)

- Load/stress test scenarios (k6/Locust).
- Automated verification for Prometheus metrics.
- Larger batch regression with extended datasets.
