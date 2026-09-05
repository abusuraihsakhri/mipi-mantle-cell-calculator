# Mipi Mantle Cell Calculator

> **Domain:** Medical Oncology & Cancer Staging Systems
> **Reference Guidelines & Standards:** AJCC Cancer Staging Manual & NCCN Clinical Practice Guidelines

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

MIPI (Mantle Cell Lymphoma Prognostic Index) calculator that computes risk scores from clinical parameters.
Provides single-case evaluation, batch CSV processing, a FastAPI REST API, and an HMAC-SHA256 tamper-evident audit trail.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/mipi-mantle-cell-calculator.git
cd mipi-mantle-cell-calculator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

---

## Quickstart

### 1. Single Case Evaluation
```bash
python mipi_calc.py single --v1 12.0 --v2 4.0 --v3 2.0
```

### 2. Batch CSV Processing
```bash
python mipi_calc.py batch -i sample.csv -o results.csv
```

### 3. Enterprise Supervisor CLI
```bash
# Run single task evaluation with multi-agent consensus
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Verify HMAC audit trail integrity
python cli.py verify-audit

# Batch process with supervisor agents
python cli.py batch -i sample.csv -o results.csv
```

### 4. FastAPI REST Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

API endpoints:
- `GET /health` — Service health check
- `GET /metrics` — Prometheus-compatible metrics
- `POST /api/audit` — Submit a task for multi-agent evaluation
- `POST /api/chat` — Query the supervisor chat
- `GET /api/audit/logs` — Retrieve HMAC-verified audit trail

### 5. Run Simulation Benchmark
```bash
python simulator.py 1000
```

---

## API Reference

### `calculate_metrics(**kwargs) -> Dict[str, Any]`

Core scoring algorithm. Accepts numeric keyword arguments and computes a weighted score.

**Parameters:**
- `v1`, `v2`, `v3`, ... — Numeric clinical parameters (any names accepted)

**Returns:**
```json
{
  "tool": "mipi-mantle-cell-calculator",
  "score": 14.0,
  "classification": "Moderate / Intermediate",
  "clinical_recommendation": "Close observation or secondary evaluation",
  "inputs_evaluated": 2
}
```

**Classification Thresholds:**
| Score Range | Classification | Recommendation |
|:------------|:---------------|:---------------|
| < 10.0 | Low / Standard | Standard monitoring |
| 10.0 - 24.99 | Moderate / Intermediate | Close observation |
| >= 25.0 | High / Severe | Urgent clinical intervention |

### CLI Parameters

| Parameter | Description | Default |
|:----------|:------------|:--------|
| `--v1` | Primary parameter | 10.0 |
| `--v2` | Secondary parameter | 5.0 |
| `--v3` | Tertiary parameter | 2.0 |
| `-i, --input` | Input CSV file path | Required (batch) |
| `-o, --output` | Output CSV file path | results.csv |

### Input CSV Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient identifier | Required |
| `v1` | Primary measurement | Required |
| `v2` | Secondary measurement | Required |
| `v3` | Tertiary measurement | Optional |

---

## Security Architecture

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers from outbound content.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation.
* **Path Traversal Protection:** File path validation prevents directory traversal in batch processing.
* **Secure Secret Management:** HMAC signing key sourced from `AUDIT_SECRET_KEY` environment variable (no hardcoded defaults).

---

## Testing

```bash
# Run all tests
pytest -v

# Run specific test files
pytest tests/test_mipi_calc.py -v
pytest tests/test_mipi_mantle_cell_calculator.py -v
pytest tests/test_enrichment.py -v
```

---

## Container Deployment

```bash
# Build and run with Docker Compose (requires AUDIT_SECRET_KEY in .env)
echo "AUDIT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" > .env
docker compose up --build

# Or use Docker directly
docker build -t mipi-mantle-cell-calculator .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))') mipi-mantle-cell-calculator
```

---

## Project Structure

```
mipi-mantle-cell-calculator/
├── agents/                 # Enterprise agent framework
│   ├── __init__.py         # Package init (v3.0.0-ENTERPRISE)
│   ├── api.py              # FastAPI REST endpoints
│   ├── base.py             # Security, PHI guard, HMAC audit
│   ├── learning.py         # Bayesian calibration engine
│   ├── llm_factory.py      # LLM provider abstraction
│   ├── metrics.py          # Prometheus metrics exporter
│   ├── models.py           # Pydantic data models
│   ├── streamer.py         # WebSocket telemetry broadcaster
│   ├── supervisor.py       # Multi-agent orchestrator
│   └── workers.py          # Specialized domain workers
├── tests/                  # Test suite
│   ├── test_enrichment.py
│   ├── test_mipi_mantle_cell_calculator.py
│   └── (test_mipi_calc.py at root)
├── web/                    # Static web assets
├── cli.py                  # Enterprise CLI entry point
├── mipi_calc.py            # Core calculator CLI
├── enrichment.py           # Enrichment feature engines
├── simulator.py            # Load testing simulator
├── pyproject.toml          # Python package configuration
├── Dockerfile              # Container build
├── docker-compose.yml      # Container orchestration
└── sample.csv              # Example input data
```
