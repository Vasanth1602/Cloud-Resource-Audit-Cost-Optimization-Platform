# Cloud Resource Audit & Cost Optimization Platform

A production-oriented AWS governance platform built for DevOps, Security, and FinOps teams. Provides continuous multi-region resource discovery, policy-based violation detection, risk scoring, cost intelligence, and remediation guidance through a REST API and operational dashboard.

---

## Executive Summary

Cloud environments without continuous governance degrade quickly — untagged resources evade cost attribution, idle EC2 instances accumulate EBS charges, orphaned EIPs and snapshots persist indefinitely, and S3 buckets grow without lifecycle bounds. At scale, this typically represents 20–35% of total AWS spend.

This platform addresses that gap by acting as a continuous audit engine:
- Scans AWS resources across regions and evaluates them against extensible governance and cost rules
- Scores each resource for risk, surfaces actionable findings via REST API and real-time dashboard
- Replaces ad-hoc Console inspection and spreadsheet audits with a reproducible, automated process
- Runs in **audit-only mode** by default — no resources are modified without an explicit remediation workflow
- Supports both **live AWS mode** and **structured mock mode** for local development and CI
- Designed as the foundation for a production internal platform, not a one-off script

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend  (React / Vite)                      │
│   Dashboard · Resource Tables · Violations Panel · Cost View     │
└────────────────────────────┬────────────────────────────────────┘
                             │  REST / JSON  (/api/v1)
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI Application Layer                     │
│  /scans  ·  /resources  ·  /violations  ·  /costs  ·  /settings │
└──────────┬─────────────────┬────────────────────────┬───────────┘
           │                 │                         │
  ┌────────▼───────┐ ┌───────▼────────┐    ┌──────────▼─────────┐
  │ Scanner Engine │ │  Rules Engine  │    │    Cost Engine      │
  │ EC2 · EBS · S3 │ │  ec2_rules    │    │  cost_explorer.py  │
  │ RDS · EIP      │ │  storage_rules│    │  CE API (MONTHLY)  │
  │ Snapshot       │ │  governance/  │    │  waste estimation  │
  └────────┬───────┘ └───────┬────────┘    └──────────┬─────────┘
           └─────────────────┴─────────────────────────┘
                             │
           ┌─────────────────▼────────────────────────┐
           │          In-Memory Session Store          │
           │  scan_sessions · resources · violations   │
           └─────────────────┬────────────────────────┘
                             │
           ┌─────────────────▼────────────────────────┐
           │             AWS Cloud APIs                │
           │  EC2 · S3 · RDS · CloudWatch · Cost Explorer │
           └──────────────────────────────────────────┘
```

| Component | Responsibility |
|---|---|
| **Scanner Engine** | Per-resource-type boto3 modules; normalize responses to a consistent schema; CloudWatch metric augmentation |
| **Rules Engine** | Stateless, deterministic rule functions; output structured violations with rule ID, severity, and remediation |
| **Cost Engine** | `ce:GetCostAndUsage` integration; MTD spend by service/region; waste estimation from violation signals |
| **Session Store** | In-process dict store keyed by scan UUID; supports disk persistence for restart recovery |
| **API Layer** | Scan jobs as FastAPI BackgroundTasks; results served via paginated resource, violation, and cost endpoints |

**Data flow:** `POST /scans` → BackgroundTask → Scanners (region × type) → Rules Engine → Risk Scoring → Cost Engine → Store → Client polls → Results served

---

## Core Capabilities

### Governance
- Multi-region resource discovery: EC2, EBS, S3, RDS, EIP, Snapshots
- Mandatory tag enforcement (`Environment`, `Owner`, `Project`) across all resource types
- Public access detection: EC2 public IPs, S3 block public access
- Encryption-at-rest checks: EBS volumes, RDS instances
- Security group exposure flagging for EC2

### Cost Intelligence
- Idle EC2 detection: 7-day avg CPU < 5% flagged as waste (rule EC2-002)
- EC2 rightsizing: one-size-down suggestions for m5, m6i, c5, c6i, r5, t3 families at < 20% CPU
- Stopped EC2 flagged for ongoing EBS accumulation
- Unattached EBS volumes estimated at `$0.10/GB/month`
- Unassociated EIPs flagged at `~$3.60/month`
- Orphaned snapshots (> 30 days, no AMI link) estimated at `$0.05/GB/month`
- S3 idle detection: no CloudWatch activity for 90+ days
- gp2 → gp3 migration recommendation (zero downtime, ~20% cost reduction)
- S3 lifecycle policy enforcement to prevent unbounded storage growth
- MTD AWS spend breakdown by service and region via Cost Explorer

### Remediation
- Every violation includes a `recommendation` field — concrete, actionable, machine-readable
- All findings persisted per scan session (immutable once written) — suitable for compliance audit trails
- Violations API consumable by downstream automation: Jira, Slack, runbook tools
- Full traceability: scan ID · resource ID · region · rule ID · severity · timestamp

### Observability
- Structured JSON logging throughout scanner, rules, and API layers
- Scanner failures isolated per resource type per region — partial results always returned
- Scan session state machine: `pending → running → completed/failed`
- `/health` liveness endpoint
- Configurable log level via `LOG_LEVEL` env var; stdout-native for container log collection

---

## Technology Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI 0.115 |
| **Runtime** | Python 3.11 |
| **AWS SDK** | boto3 1.35 |
| **Config** | pydantic-settings (env file + environment variable resolution) |
| **Background Jobs** | FastAPI BackgroundTasks |
| **Frontend** | React 18 + Vite |
| **HTTP Client** | Axios with request/response interceptors |
| **Routing** | react-router-dom v6 |
| **Containerization** | Docker (multi-stage frontend build, Python slim backend) |
| **Reverse Proxy** | Nginx (`/api/v1` proxy pass to FastAPI) |
| **Orchestration** | Docker Compose (local); ECS/Kubernetes-compatible |
| **Testing** | pytest + moto (AWS service mocking) |

**AWS APIs used:** `ec2:Describe*` · `s3:List*` · `s3:GetBucket*` · `rds:DescribeDBInstances` · `cloudwatch:GetMetricStatistics` · `ce:GetCostAndUsage`

---

## Deployment

### Docker Compose (Recommended)

```bash
git clone https://github.com/Vasanth1602/Cloud-Resource-Audit-Cost-Optimization-Platform.git
cd Cloud-Resource-Audit-Cost-Optimization-Platform
cp .env.example .env          # Set MOCK_AWS=true for local demo
docker-compose up --build
```

- Backend (FastAPI): `http://localhost:8000`
- Frontend (Nginx): `http://localhost:80`

### Local Development

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
```

### Environment Configuration

```env
APP_ENV=production
MOCK_AWS=false
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
SCAN_REGIONS=us-east-1,us-west-2,ap-south-1
CORS_ORIGINS=https://your-internal-domain.com
```

### Security Notes
- Requires **read-only IAM permissions only** — `ec2:Describe*`, `s3:Get*`, `rds:Describe*`, `cloudwatch:GetMetricStatistics`, `ce:GetCostAndUsage`
- **IAM role attachment** (EC2 instance profile / ECS task role) is the recommended credential strategy — avoid static credentials in production
- **STS AssumeRole** supported via `aws_role_arn` config for cross-account scanning
- Deploy behind an internal load balancer; API is not intended for direct public exposure
- Bearer token interceptor scaffolded; JWT middleware ready for IdP integration

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/routes/        # Scan, settings, health endpoints
│   │   ├── core/              # Config (pydantic-settings), in-memory store, logging
│   │   ├── services/
│   │   │   ├── scanner/       # One boto3 module per resource type
│   │   │   ├── rules_engine/  # Stateless rule functions + risk scoring
│   │   │   ├── cost_engine/   # Cost Explorer integration
│   │   │   └── governance/    # Tag validation, encryption checks, security group checks
│   │   └── utils/             # Centralized boto3 client factory (with AssumeRole support)
│   └── tests/                 # pytest suite with moto-based AWS mocking
│
├── frontend/
│   ├── src/
│   │   ├── pages/             # Dashboard (resource/violation/cost views), Settings
│   │   ├── components/        # Sidebar, shared UI
│   │   └── services/          # Axios client, settings API helpers
│   └── nginx.conf             # /api/v1 proxy pass configuration
│
├── infra/                     # Infrastructure-as-code (extensible)
├── .env.example               # Documented reference configuration
├── docker-compose.yml
└── Makefile                   # Developer workflow automation
```

> Detailed internal documentation is being migrated to:
> - `docs/architecture.md` — component design and data flow
> - `docs/security.md` — IAM policy reference, STS patterns, secrets management
> - `docs/cost-model.md` — rule-to-waste mapping, pricing assumptions
> - `docs/remediation.md` — violation structure, integration patterns

---

## Roadmap

### Phase 1 — Core Audit Engine _(Current)_
- Multi-region discovery: EC2, EBS, EIP, S3, Snapshots, RDS
- 10+ governance and cost rules with severity classification and risk scoring
- Real-time scan API with background task execution and polling
- Operational dashboard with resource tables, violations panel, cost view
- Mock mode for CI and demo environments; Docker Compose deployment

### Phase 2 — Operational Depth
- Persistent store (PostgreSQL) replacing in-memory session store
- Scan history and violation trend tracking across sessions
- Cost anomaly detection using week-over-week Cost Explorer data
- Slack / webhook notification integration for CRITICAL and HIGH findings
- CLI export for JSON/CSV audit report generation
- Extended rightsizing using p95 CPU (vs. avg); Lambda and NAT Gateway scanners
- Scheduled scan automation with cron triggers

### Phase 3 — Enterprise Enhancements
- Multi-account scanning via STS AssumeRole across an AWS Organization
- Role-based access control with account-scoped read permissions
- Policy-as-code: external rule definitions in YAML loaded at runtime
- Remediation execution layer with approval gates, dry-run mode, and audit log
- AWS Config integration for continuous compliance evaluation between scans
- Terraform/CloudFormation drift detection
- Prometheus metrics endpoint + Grafana dashboard integration
- SOC 2 / CIS Benchmark compliance report export

---

*Architecture documentation, IAM policy reference, and cost model details are documented in `docs/` (in progress).*
