# Cloud Resource Audit & Cost Optimization Platform

A production-oriented AWS governance and FinOps platform. Scans EC2, EBS, S3, RDS, EIP, Snapshots, Load Balancers, and NAT Gateways across multiple regions — then surfaces violations, risk scores, cost waste, ranked savings recommendations, and downloadable reports through a REST API and real-time dashboard.

> **20+ rule IDs · 8 resource types · 5 intelligence layers**

---

## What It Does

| Layer | Capability |
|---|---|
| **Scanner Engine** | Multi-region boto3 discovery for EC2, EBS, S3, RDS, EIP, Snapshots, ALB/NLB, NAT Gateways |
| **Rules Engine** | 20+ deterministic rules: idle detection, tagging, encryption, rightsizing, Spot eligibility, RI candidacy |
| **Cost Intelligence** | MTD spend via Cost Explorer, 14-day daily trend sparkline, waste-by-service, cost-by-tag (Environment) |
| **Recommendations** | Violation → ranked savings action mapping; per-rule dollar estimates; sorted by highest savings first |
| **Export Engine** | Download violations CSV, recommendations CSV, full JSON bundle, or print-ready HTML report (→ PDF) |

---

## Prerequisites

- Python 3.9+
- Node.js 18+
- Git
- AWS credentials *(or use `MOCK_AWS=true` for a fully offline demo — no AWS account needed)*

---

## How to Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/Vasanth1602/Cloud-Resource-Audit-Cost-Optimization-Platform.git
cd Cloud-Resource-Audit-Cost-Optimization-Platform
```

---

### 2. Configure environment

```bash
cp .env.example .env
```

The `.env` file has two modes — pick one:

**Mode A — Offline demo (no AWS account needed):**
```env
MOCK_AWS=true   # ← default, realistic mock data generated automatically
```

**Mode B — Real AWS scan:**
```env
MOCK_AWS=false  # AWS credentials are entered via the Settings page in the UI
                # You do NOT need to put your keys in this file
```

The only values you may want to change:
```env
APP_ENV=development
APP_VERSION=1.0.0
LOG_LEVEL=INFO

MOCK_AWS=true               # flip to false to scan real AWS

AWS_ACCESS_KEY_ID=          # leave blank — enter via Settings UI at runtime
AWS_SECRET_ACCESS_KEY=      # leave blank — enter via Settings UI at runtime

AWS_REGION=ap-south-1
SCAN_REGIONS=ap-south-1     # comma-separated, e.g. ap-south-1,us-east-1

CORS_ORIGINS=http://localhost:3000,http://localhost:5173

SLACK_WEBHOOK_URL=          # optional
```

---

### 3. Start the backend

**Windows (PowerShell):**
```powershell
cd backend
python -m venv ..\venv
..\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**macOS / Linux:**
```bash
cd backend
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend running at **http://localhost:8000**  
Swagger docs at **http://localhost:8000/docs**

---

### 4. Start the frontend

Open a **new terminal** (keep backend running):

```bash
cd frontend
npm install
npm run dev
```

Frontend running at **http://localhost:3000**

---

### 5. Run your first scan

1. Open **http://localhost:3000**
2. Go to **Settings** → enter AWS credentials (or leave as-is for mock mode)
3. Click **Run Scan**
4. Resources, violations, costs, and recommendations populate in real time

---

## Run Tests

```bash
cd backend
# Windows:   ..\venv\Scripts\activate
# macOS/Linux: source ../venv/bin/activate

pytest tests/ -v
```

Expected: **20 passed**

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/scans` | Trigger a new scan |
| `GET` | `/api/v1/scans` | List all scan sessions |
| `GET` | `/api/v1/scans/{id}` | Scan status + metadata |
| `GET` | `/api/v1/scans/{id}/resources` | Paginated resource list |
| `GET` | `/api/v1/scans/{id}/violations` | Violations with severity summary |
| `GET` | `/api/v1/scans/{id}/costs` | Cost summary (trend, tags, waste) |
| `GET` | `/api/v1/scans/{id}/recommendations` | Ranked savings recommendations |
| `GET` | `/api/v1/scans/{id}/export/violations.csv` | ⬇ Violations CSV |
| `GET` | `/api/v1/scans/{id}/export/recommendations.csv` | ⬇ Recommendations CSV |
| `GET` | `/api/v1/scans/{id}/export/report.json` | ⬇ Full scan JSON bundle |
| `GET` | `/api/v1/scans/{id}/export/report.html` | ⬇ Print-ready HTML report (→ PDF via Ctrl+P) |
| `GET` | `/api/v1/health` | Liveness check |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend  (React 18 / Vite)                   │
│  Dashboard · Violations · Cost Intelligence · Recommendations    │
└────────────────────────────┬────────────────────────────────────┘
                             │  REST / JSON  (/api/v1)
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI Application Layer                     │
│  /scans · /resources · /violations · /costs · /recommendations  │
│  /export/*.csv  ·  /export/report.html  ·  /settings            │
└──────────┬─────────────────┬──────────────────┬─────────────────┘
           │                 │                  │
  ┌────────▼───────┐ ┌───────▼────────┐ ┌───────▼──────────────┐
  │ Scanner Engine │ │  Rules Engine  │ │ Cost + Export Engine  │
  │ EC2 · EBS · S3 │ │ 20+ rules      │ │ CE API · daily trend  │
  │ RDS · EIP      │ │ ec2/rds/lb/    │ │ waste-by-service      │
  │ Snapshot       │ │ nat/storage    │ │ CSV · JSON · HTML/PDF │
  │ LB · NAT GW    │ │ governance     │ └──────────────────────┘
  └────────────────┘ └────────────────┘
                    │
        ┌───────────▼──────────────────┐
        │   In-Memory Store + JSON file │  (survives restarts)
        └───────────┬──────────────────┘
                    │
        ┌───────────▼──────────────┐
        │      AWS Cloud APIs      │
        │  EC2 · S3 · RDS · CW     │
        │  Cost Explorer           │
        └──────────────────────────┘
```

---

## Rules Reference

| Rule ID | Resource | Severity | Finding |
|---|---|---|---|
| EC2-001 | EC2 | MEDIUM | Stopped instance — EBS still billing |
| EC2-002 | EC2 | HIGH | Idle — avg CPU < 5% over 7 days |
| EC2-003 | EC2 | LOW | Missing mandatory tags |
| EC2-004 | EC2 | LOW | Public IP assigned |
| EC2-005 | EC2 | MEDIUM | Oversized — rightsize one class down |
| EC2-006 | EC2 | LOW | Not in Auto Scaling Group |
| EC2-007 | EC2 | MEDIUM | Spot-eligible On-Demand instance |
| EC2-008 | EC2 | LOW | RI candidate — running > 30 days On-Demand |
| EBS-001 | EBS | HIGH | Unattached volume |
| EBS-002 | EBS | CRITICAL | Unencrypted volume |
| EBS-003 | EBS | LOW | gp2 → gp3 migration opportunity |
| S3-001 | S3 | CRITICAL | Public access not blocked |
| S3-002 | S3 | MEDIUM | Versioning disabled |
| S3-003 | S3 | HIGH | No lifecycle policy |
| S3-004 | S3 | LOW | Idle bucket — no activity for 90 days |
| EIP-001 | EIP | MEDIUM | Unassociated Elastic IP (~$3.60/mo) |
| SNAPSHOT-001 | Snapshot | LOW | Orphaned snapshot > 30 days |
| LB-001 | Load Balancer | LOW | Low-traffic LB (< 10 req/day) |
| LB-002 | Load Balancer | HIGH | No listeners — serving zero traffic |
| NAT-001 | NAT Gateway | HIGH | < 1 GB transferred in 7 days (~$32/mo) |
| RDS-001 | RDS | HIGH | Idle DB — fewer than 5 connections |
| RDS-002 | RDS | MEDIUM | Over-provisioned large class, CPU < 20% |
| RDS-003 | RDS | LOW | Storage autoscaling disabled |

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/routes/         # audit.py, settings.py, health.py
│   │   ├── core/               # config.py, store.py, logging.py
│   │   └── services/
│   │       ├── scanner/        # ec2, ebs, s3, rds, eip, snapshot, lb, nat
│   │       ├── rules_engine/   # ec2, rds, lb, nat, storage rules
│   │       ├── cost_engine/    # cost_explorer.py
│   │       ├── recommendations.py
│   │       └── export_engine.py
│   ├── tests/                  # 20 pytest tests (moto-mocked AWS)
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── pages/              # Dashboard, Recommendations, Settings
    │   ├── components/         # Sidebar
    │   └── services/           # apiClient, settingsService
    └── package.json
```

---

## IAM Permissions (Read-Only)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:Describe*",
      "elasticloadbalancing:Describe*",
      "s3:ListAllMyBuckets",
      "s3:GetBucket*",
      "rds:DescribeDBInstances",
      "cloudwatch:GetMetricStatistics",
      "ce:GetCostAndUsage"
    ],
    "Resource": "*"
  }]
}
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9 · FastAPI · uvicorn |
| AWS SDK | boto3 |
| Frontend | React 18 · Vite · react-router-dom v6 |
| Testing | pytest · moto |

---

## Roadmap

- [ ] PostgreSQL persistence (replace file-based store)
- [ ] Scheduled scans with cron triggers
- [ ] Slack / webhook alerts for CRITICAL findings
- [ ] Multi-account scanning via STS AssumeRole
- [ ] SOC 2 / CIS Benchmark compliance report export

---

*Built with FastAPI · React · boto3 · moto*
