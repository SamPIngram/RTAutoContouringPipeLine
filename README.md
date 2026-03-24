# RT Auto-Contouring Pipeline

An end-to-end radiotherapy auto-contouring platform for data ingestion, dataset curation, model training (nnU-Net), validation, and clinical deployment.

## Architecture

Modular, containerized microservices:

| Service | Technology | Purpose |
|---|---|---|
| Backend API | FastAPI + Python 3.11 | Routing, orchestration, webhooks |
| Task Queue | Celery + Redis | Async jobs: conversion, training, inference |
| DICOM Engine | Orthanc | DICOM SCP/SCU node |
| Database | PostgreSQL / SQLite | Metadata, model registry, audit logs |
| Frontend | React 18 + Vite | SPA for dataset curation and monitoring |

## Quick Start (Docker)

```bash
cp .env.example .env
# Edit .env with your settings

docker compose up --build
```

- Backend API + docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Orthanc UI: http://localhost:8042

## Local Development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync --dev

# Run backend
uv run uvicorn backend.main:app --reload

# Run Celery worker
uv run celery -A backend.celery_app worker --loglevel=info

# Run tests
uv run pytest tests/

# Lint
uv run ruff check .
```

## Configuration

### Global Config (`config.toml`)

System-wide settings: Orthanc credentials, database URL, Redis URL, GPU limits, base data paths.

### Deployment Configs (`deployments/*.toml`)

Each file defines a clinical workflow trigger. See `deployments/example_prostate_t2.toml` for a full example.

```toml
[workflow]
name = "Prostate_Routine_T2"
trigger = "orthanc_new_study"

[inference]
model_id = "nnunet_prostate_v1.2"
fallback_to_cpu = true

[export]
generate_rtstruct = true
destination_type = "dicom_node"
destination_aet = "CLINICAL_TPS"
```

## Modules

| Module | Description |
|---|---|
| **Ingestion** | Orthanc webhooks, folder watcher, ProKnow sync |
| **Preprocessing** | DICOM → NIfTI conversion with resampling/orientation |
| **Training** | nnU-Net v2 orchestration via ephemeral Docker containers |
| **Validation** | Dice + HD95 metrics, NiiVue overlay viewer |
| **Deployment** | TOML-driven runner, RTSTRUCT generation via rt-utils |

## Audit & Surveillance

All data movements, training jobs, and inference runs are logged to the database with structured JSON logs. Access via `GET /api/audit/logs`.

See [design.md](design.md) for the full system design document.
