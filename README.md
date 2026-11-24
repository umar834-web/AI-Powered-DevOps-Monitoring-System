[README_AI_Powered_DevOps_Monitoring.md](https://github.com/user-attachments/files/35334900/README_AI_Powered_DevOps_Monitoring.md)
# AI-Powered DevOps Monitoring & Incident Detection System

A Windows-focused infrastructure monitoring prototype that collects system metrics, exposes them in Prometheus format, generates threshold alerts, and uses a locally running Llama 3.2 model through Ollama to produce human-readable incident analysis and troubleshooting guidance.

**Project repository:** https://github.com/umar834-web/AI-Powered-DevOps-Monitoring-System

## Project overview

Traditional monitoring can show that a resource is under pressure, but an engineer may still need to investigate what the alert means and what to check next. This project combines metric collection and threshold-based alerting with an AI-assisted analysis layer. The AI output is intended to support an engineer; it is not treated as a verified root cause or an autonomous remediation decision.

The supplied implementation contains:
- A Python Windows monitoring agent using `psutil`.
- A Prometheus-compatible metrics exporter.
- A FastAPI alert receiver and API.
- Local incident analysis through Ollama and the `llama3.2` model.
- A React/Vite dashboard for live metrics, alerts, and analysis.
- Controlled evaluation datasets, rule-based baseline code, LLM experiment scripts, and saved result files.

## Main features

- Collects CPU, memory, disk, network-counter, and system-uptime metrics.
- Exposes metrics at `http://localhost:8000/metrics`.
- Uses configurable thresholds for CPU, memory, and disk alerts.
- Sends alert payloads to the FastAPI receiver.
- Provides API routes to receive alerts, list alerts, retrieve live metrics, and request AI analysis.
- Uses a local LLM to produce an incident summary, observed facts, possible causes, recommended actions, severity assessment, and next steps.
- Includes an evaluation area for comparing deterministic rule-based classification with Llama 3.2 outputs.

## Architecture and data flow

```text
Windows host
    |
    v
monitor.py (psutil collection)
    |
    +---- Prometheus-format metrics :8000/metrics
    |
    +---- threshold alert POST
                 |
                 v
       alert_receiver.py (FastAPI :8001)
                 |
          +------+------+
          |             |
          v             v
    React dashboard   Ollama :11434
    (Vite :5173)      llama3.2
          |             |
          +------<------+
          displays AI incident analysis
```

The FastAPI service also reads the exported metrics endpoint to provide live metric data to the frontend. The receiver accepts alert payloads in a Grafana-compatible structure. The provided source files do not include a Prometheus server configuration or Grafana provisioning/dashboard configuration; those services must be configured separately if they are used in a deployment.

## Technology stack

| Component | Technology | Purpose |
|---|---|---|
| Monitoring agent | Python, `psutil` | Reads Windows system metrics |
| Metrics exporter | `prometheus_client` | Exposes metrics in Prometheus exposition format |
| Backend/API | FastAPI, Uvicorn, Requests | Receives alerts, serves metrics and invokes AI analysis |
| Local AI runtime | Ollama, Llama 3.2 | Generates incident explanations and troubleshooting guidance |
| Frontend | React, Vite, JavaScript, CSS | Dashboard interface |
| Visualisation | Recharts | Experimental charts |
| Icons | lucide-react | Dashboard icons |
| Evaluation | Python, JSON datasets | Compares rule-based and LLM classifications |

## Repository layout

The project is organised into backend/monitoring, frontend, and evaluation components. Keep the actual folder names from the uploaded source when arranging the repository.

```text
AI-Powered-DevOps-Monitoring-System/
├── backend/
│   ├── alert_receiver.py
│   ├── monitor.py
│   └── monitor_backup.py
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── index.html
│   ├── analysis.html
│   └── src/
│       ├── App.jsx
│       ├── Analysis.jsx
│       └── stylesheets and assets
└── evaluation/
    ├── dataset.json
    ├── dataset_v2.json
    ├── rule_baseline.py
    ├── llm_analyzer.py
    ├── llm_analyzer_v3.py
    ├── evaluate.py
    ├── evaluate_v3.py
    └── results/
```

## Prerequisites

Install the following on the Windows machine:

- Python 3.10 or later (the supplied virtual-environment files indicate Python 3.12 was used in that environment; recreate a clean environment rather than copying the virtual environment).
- Node.js and npm compatible with the Vite version in `frontend/package.json`.
- Ollama, with the `llama3.2` model available locally.
- Python packages: `fastapi`, `uvicorn`, `psutil`, `prometheus-client`, and `requests`.

Prometheus and Grafana are optional external services for a fuller monitoring deployment. Their configuration files are not included in the supplied ZIP archives.

## Installation and execution

### 1. Prepare the Python environment

From the backend/monitoring directory, create and activate a fresh virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install fastapi uvicorn psutil prometheus-client requests
```

### 2. Start Ollama

Install and start Ollama, then download the model:

```powershell
ollama pull llama3.2
ollama run llama3.2
```

Keep Ollama running so the FastAPI service can reach `http://localhost:11434`.

### 3. Start the FastAPI receiver

From the directory containing `alert_receiver.py`:

```powershell
uvicorn alert_receiver:app --host 127.0.0.1 --port 8001 --reload
```

The receiver is configured for the local frontend origin `http://localhost:5173`.

### 4. Start the Windows monitoring agent

In a separate terminal, from the directory containing `monitor.py`:

```powershell
python monitor.py
```

The agent exposes metrics at `http://localhost:8000/metrics` and sends threshold alerts to the receiver at `http://localhost:8001/api/alerts`.

### 5. Start the frontend

From the frontend directory:

```powershell
npm install
npm run dev
```

Open the local Vite URL shown in the terminal (the source frontend is configured to call the API at `http://localhost:8001`).

### 6. Check the services

- Metrics exporter: `http://localhost:8000/metrics`
- FastAPI health endpoint: `http://localhost:8001/`
- FastAPI interactive API documentation: `http://localhost:8001/docs`
- Frontend: the Vite development URL, normally `http://localhost:5173`

Run the monitoring agent, FastAPI receiver, Ollama, and frontend in separate terminals/processes. The live metrics endpoint requires the monitoring agent to be running.

## Incident detection and AI analysis

The monitoring agent currently configures thresholds of:
- CPU: 80%
- Memory: 85%
- Disk: 90%

When a monitored value crosses its configured threshold, the agent creates an alert payload and posts it to the FastAPI receiver. The agent tracks whether an alert is already active for each monitored component to reduce repeated notifications while the metric remains above its threshold. A new alert can be sent after the metric recovers and breaches again.

When an incident is sent for analysis, the backend extracts alert labels and annotations, identifies the affected component, and builds a component-aware prompt. The prompt asks the model to separate observed facts from possible causes, avoid inventing a confirmed root cause, and recommend safe investigation steps. The resulting text is returned to the frontend for display.

## Experimental evaluation

The supplied evaluation code uses a controlled 30-case dataset (`dataset_v2.json`) with normal, threshold-boundary, high/critical, multiple-resource, and incomplete-telemetry scenarios. It compares a deterministic rule-based baseline with Llama 3.2 outputs across diagnosis, severity, and action-category classification.

The saved result files report:

| Evaluation run | Cases | Diagnosis accuracy | Severity accuracy | Action accuracy | Mean LLM response time |
|---|---:|---:|---:|---:|---:|
| Initial LLM experiment | 10 | 70.00% | 60.00% | 70.00% | 10.358 s |
| Llama 3.2 experiment 2 | 30 | 63.33% | 66.67% | 63.33% | 10.517 s |
| Rule-Guided Llama experiment 3 | 30 | 56.67% | 53.33% | 43.33% | 4.766 s |
| Rule-based baseline on 30 cases | 30 | 100.00% | 100.00% | 100.00% | Not applicable |

These are the recorded results in the supplied JSON output files, not a claim of performance on production incidents. The rule-based baseline is evaluated against a controlled dataset whose labels follow explicit threshold rules, so its perfect score should be interpreted within that benchmark's scope. The LLM results show that the tested model did not outperform the deterministic baseline on these classification metrics. The LLM's intended additional role in the application is to generate contextual explanations and investigation guidance.

### Reproducing the evaluation

The evaluation scripts expect to be run from the evaluation directory and use relative file paths. Ensure the Ollama service and `llama3.2` model are available before running an LLM experiment. The evaluation scripts and JSON files should be reviewed together before repeating an experiment. Response times can vary with hardware, model loading, and runtime conditions.

## Limitations

- The evaluation data is controlled and manually prepared; it is not a large production incident corpus.
- The rule baseline is aligned with the dataset's explicit threshold-based ground-truth rules.
- The LLM can misclassify the incident, severity, or action category.
- AI-generated possible causes are hypotheses and require engineer verification.
- The current monitoring agent collects a limited set of host metrics and does not by itself establish process-level root cause.
- The supplied source does not include full Prometheus server or Grafana deployment configuration.
- Alert and incident storage in the FastAPI code is in memory and is not persistent across application restarts.

## Team

| Name | Enrollment number |
|---|---|
| Mohd Umar | 230834 |
| Priyanshu Mishra | 230802 |

## Repository

[https://github.com/umar834-web/AI-Powered-DevOps-Monitoring-System](https://github.com/umar834-web/AI-Powered-DevOps-Monitoring-System)

## Responsible use

This project is an academic prototype. AI-generated analysis is advisory only. Engineers should verify observations and recommendations against system telemetry and operational policies before taking corrective action.
