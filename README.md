# Cloud Resource Audit & Cost Optimization Platform

A production-oriented AWS governance platform that provides continuous cloud resource discovery, policy-based violation detection, cost intelligence, and remediation guidance across multi-region environments. Designed for use by DevOps, Security, and FinOps teams operating at scale.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Core Capabilities](#3-core-capabilities)
4. [Technical Stack](#4-technical-stack)
5. [Governance & Policy Model](#5-governance--policy-model)
6. [Cost Optimization Strategy](#6-cost-optimization-strategy)
7. [Remediation Philosophy](#7-remediation-philosophy)
8. [Observability & Reliability](#8-observability--reliability)
9. [Security Model](#9-security-model)
10. [Deployment Strategy](#10-deployment-strategy)
11. [Project Structure](#11-project-structure)
12. [Roadmap](#12-roadmap)
13. [Why This Project Matters](#13-why-this-project-matters)

---

## Getting Started

This section covers everything needed to clone, configure, and run the platform locally — either with mock data (no AWS account required) or pointed at a real AWS account.

### Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.11 | Backend runtime |
| Node.js | 18 LTS | Frontend build |
| Docker + Docker Compose | Docker 24+ | For containerized setup |
| Git | Any | — |
| AWS credentials | — | Only needed for live mode (`MOCK_AWS=false`) |

---

### Option A — Docker Compose (Recommended)

The fastest path to a running instance. No Python or Node.js setup required on the host.

**Step 1 — Clone the repository**

```bash
git clone https://github.com/Vasanth1602/Cloud-Resource-Audit-Cost-Optimization-Platform.git
cd Cloud-Resource-Audit-Cost-Optimization-Platform
```

**Step 2 — Create your environment file**

```bash
cp .env.example .env
```

Open `.env` and set:

```env
# To run with realistic mock data (no AWS account needed):
MOCK_AWS=true

# To scan a real AWS account, set MOCK_AWS=false and add credentials:
# MOCK_AWS=false
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
# AWS_DEFAULT_REGION=us-east-1
# SCAN_REGIONS=us-east-1,us-west-2
```

> **Never commit `.env` to version control.** It is listed in `.gitignore` and must stay local.

**Step 3 — Build and start all services**

```bash
docker-compose up --build
```

This starts two containers:
- **Backend** (FastAPI) on port `8000`
- **Frontend** (React, served via Nginx) on port `80` — proxying `/api/v1` to the backend

**Step 4 — Open the dashboard**

```
http://localhost
```

If `MOCK_AWS=true`, the app will be connected immediately with a mock AWS environment. Click **Scan Now** to run your first audit.

---

### Option B — Manual Local Development

Use this if you want hot-reload on code changes during development.

**Step 1 — Clone the repository**

```bash
git clone https://github.com/Vasanth1602/Cloud-Resource-Audit-Cost-Optimization-Platform.git
cd Cloud-Resource-Audit-Cost-Optimization-Platform
```

**Step 2 — Backend setup**

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Install dependencies
# requirements.txt lives inside backend/ — run this from within the backend/ directory
pip install -r requirements.txt
```

**Step 3 — Configure environment**

```bash
# From the project root
cp .env.example .env
```

Edit `.env` — at minimum set:

```env
MOCK_AWS=true
APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
```

**Step 4 — Start the backend**

```bash
# From the backend/ directory, with venv activated
uvicorn app.main:app --reload --port 8000
```

Verify it is running:

```
http://localhost:8000/health          → { "status": "ok" }
http://localhost:8000/docs            → Interactive Swagger API docs
```

**Step 5 — Frontend setup**

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server starts at `http://localhost:5173`. It proxies `/api/v1` calls to the backend at `localhost:8000` automatically (configured in `vite.config.js`).

**Step 6 — Open the dashboard**

```
http://localhost:5173
```

---

### Connecting to a Real AWS Account

**Step 1 — Create an IAM user or role**

Create an IAM policy with the permissions listed in [Section 9 — Security Model](#9-security-model) and attach it to a user or role. The policy is read-only; no write or delete permissions are required.

**Step 2 — Generate an access key** (if using IAM user)

In AWS Console → IAM → Users → your user → Security credentials → Create access key.

**Step 3 — Update your `.env`**

```env
MOCK_AWS=false
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=ap-south-1
SCAN_REGIONS=ap-south-1,us-east-1
```

**Step 4 — Restart the backend** (or re-run `docker-compose up --build`)

**Step 5 — Configure via the Settings page**

Navigate to **Settings** in the dashboard sidebar. Enter your AWS credentials and select your regions. Click **Test Connection** to verify. Then return to the Dashboard and click **Scan Now**.

---

### Verifying Everything Works

After triggering a scan, the dashboard will poll for completion (every 3 seconds). Once done:

- **Resources tab** — shows EC2, EBS, S3, RDS, EIP, and Snapshot inventory
- **Violations tab** — shows all detected policy and cost violations, filterable by severity
- **Costs tab** — shows month-to-date AWS spend breakdown by service and region

To verify the API directly:

```bash
# Trigger a scan
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Content-Type: application/json" \
  -d '{"regions": ["us-east-1"]}'

# Check scan status (replace <scan_id> with the id returned above)
curl http://localhost:8000/api/v1/scans/<scan_id>

# Get violations from the completed scan
curl http://localhost:8000/api/v1/scans/<scan_id>/violations
```

---

### Publishing Your Own Instance to GitHub

**Step 1 — Initialize the repository**

```bash
cd cloud-resource-audit-platform
git init
git add .
git commit -m "feat: initial commit — Cloud Resource Audit Platform"
```

**Step 2 — Create a remote repository on GitHub**

Go to [github.com/new](https://github.com/new). Do not initialize with a README (you already have one).

**Step 3 — Push**

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

**Before pushing, confirm `.env` is not tracked:**

```bash
git ls-files | grep "\.env$"
```

If `.env` appears in the output, remove it from tracking first:

```bash
git rm --cached .env
git commit -m "chore: untrack .env"
```

The `.gitignore` in this repository already excludes `.env`, `venv/`, `node_modules/`, `scan_data.json`, and all other runtime artifacts.

---

## 1. Executive Summary

Cloud environments without continuous governance degrade quickly. Untagged resources evade cost attribution. Stopped EC2 instances accumulate EBS charges. Unassociated Elastic IPs persist indefinitely. S3 buckets quietly grow without lifecycle policies. Orphaned snapshots age unnoticed. At scale, these issues translate directly into operational risk and wasted budget — often in the range of 20–35% of total AWS spend.

This platform addresses that problem by acting as a continuous audit engine: it scans AWS resources across regions, evaluates them against an extensible set of governance and cost rules, scores each resource for risk, and surfaces actionable findings through a structured API and a real-time dashboard. It is designed to replace ad-hoc AWS Console inspection and fragmented spreadsheet-based audits with a reproducible, automated, and observable process.

**Primary consumers of this platform:**

- **DevOps / Platform Engineering** — enforcing infrastructure standards and tagging policies across accounts and regions
- **Security Engineering** — detecting publicly accessible resources, unencrypted storage, and missing access controls
- **FinOps / Cloud Finance** — identifying idle, oversized, or orphaned resources driving unnecessary spend; tracking month-to-date cost by service and region

The platform runs in audit-only mode by default. No resources are modified without an explicit remediation workflow. All findings are persisted per scan session and accessible via API.

---

## 2. System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React/Vite)                     │
│  Dashboard · Resource Tables · Violations Panel · Cost View      │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST / JSON  (Axios → /api/v1)
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Application Layer                    │
│  /scans  ·  /scans/{id}/resources  ·  /violations  ·  /costs    │
│  /settings · /health                                             │
└───────┬──────────────────┬──────────────────────┬───────────────┘
        │                  │                       │
┌───────▼───────┐  ┌───────▼───────┐    ┌─────────▼──────────┐
│ Scanner Engine│  │ Rules Engine  │    │  Cost Engine        │
│  EC2  EBS S3  │  │ ec2_rules.py  │    │  cost_explorer.py   │
│  EIP  RDS     │  │ storage_rules │    │  build_cost_summary │
│  Snapshot     │  │ governance/   │    │  get_cost_data      │
└───────┬───────┘  └───────┬───────┘    └─────────┬──────────┘
        │                  │                       │
┌───────▼──────────────────▼───────────────────────▼──────────┐
│                    In-Memory Session Store                    │
│   scan_sessions · scan_resources · scan_violations · costs   │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                     AWS Cloud APIs                            │
│  EC2 · EBS · S3 · CloudWatch · Cost Explorer (ce:*)          │
└──────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**Frontend (React + Vite)**
Provides a real-time operational dashboard. Initiates scans, polls scan status, and renders scanned resources grouped by type (EC2, EBS, S3, RDS, EIP, Snapshot) alongside a violations panel filterable by severity and a cost breakdown view by service and region.

**API Layer (FastAPI)**
Handles all client-facing interactions. Scan jobs are triggered via `POST /api/v1/scans` and executed as FastAPI background tasks. Results are served through dedicated resource, violation, and cost endpoints. The settings layer manages AWS credential injection and mock/live mode switching at runtime.

**Scanner Engine**
Each resource type has a dedicated scanner module. Scanners call AWS service APIs using boto3 and normalize responses into a consistent resource schema (`resource_id`, `resource_type`, `region`, `state`, `tags`, `raw_data`). Scanners support both live AWS mode and a structured mock mode for local development and CI.

**Rules Engine**
Operates post-scan. Each resource is evaluated against type-specific rule functions that return structured violation objects with rule IDs, severity levels, messages, and remediation recommendations. Rules are grouped by domain: EC2 rules, storage rules (EBS, S3, EIP, Snapshot), encryption checks, tag validation, and security group inspection.

**Cost Engine**
Interfaces with AWS Cost Explorer (`ce:GetCostAndUsage`) to retrieve month-to-date spend grouped by service and region. The engine produces a structured cost summary including total spend, top services by spend, region breakdown, and an estimated waste figure derived from detected violations.

**In-Memory Session Store**
Scan sessions, resources, violations, and cost records are stored in-process using Python dictionaries keyed by scan ID. The store supports persistence to disk (`store.save()`) for session recovery across restarts.

### Data Flow

```
Scan Triggered → Background Task Created → Scanners Execute (region × resource_type)
→ Rules Engine Evaluates Each Resource → Risk Score Computed → Cost Engine Called
→ Results Written to Store → Client Polls for Status → Completed → Data Served via API
```

### Async Processing

Scans execute as FastAPI `BackgroundTasks`. This allows the POST endpoint to return immediately with a `scan_id`, while the scan runs asynchronously. The frontend uses a polling loop (3-second intervals, max 60 attempts) to detect completion and load results without blocking the UI.

---

## 3. Core Capabilities

### Cloud Resource Discovery

Continuous discovery across EC2 instances, EBS volumes, Elastic IPs, S3 buckets, EBS snapshots, and RDS instances. Each scan covers all specified regions. The scanner engine retrieves CloudWatch metrics (CPU utilization, S3 BucketSizeBytes) to augment raw inventory data with operational signals.

### Governance Evaluation

Resources are evaluated against a structured rule set on every scan. Each rule is explicitly coded with a rule ID, severity, message template, remediation recommendation, and compliance framework reference (FinOps, CIS-AWS, Governance). This makes findings auditable and traceable to a specific policy.

### Policy Enforcement

Mandatory tag enforcement (Environment, Owner, Project) is applied across all resource types. Public access checks are applied to EC2 and S3. Encryption checks are applied to EBS and RDS. Security group exposure is flagged for EC2 instances. These checks map directly to CIS AWS Foundations Benchmark controls.

### Cost Intelligence

Month-to-date AWS spend is retrieved from Cost Explorer, broken down by service and region. Waste is estimated by aggregating identifiable idle and orphaned resource costs (unattached EBS, unassociated EIPs, orphaned snapshots, stopped instances). This provides a service-level cost signal alongside resource-level waste attribution.

### Violation Scoring

Each resource receives a composite risk score computed from the severity distribution of its associated violations. Scores are classified into four bands: CRITICAL (≥76), HIGH (51–75), MEDIUM (26–50), LOW (1–25), and CLEAN (0). Scoring is deterministic and reproducible given the same violation set.

### Remediation Framework

Every violation includes a `recommendation` field with a concrete, actionable remediation step. Findings are exposed via the violations API endpoint, enabling downstream automation tools or on-call workflows to consume and act on them.

### Audit Logging

Structured JSON logging is applied throughout the scanner, rules engine, and API layer. Each scan session is recorded with timestamps, region scope, resource count, and violation count. Log events include scanner name, region, and failure reason for any scan errors.

### Observability

A `/health` endpoint confirms service availability. Scan session status transitions (`pending → running → completed/failed`) are tracked. Scanner-level errors are captured and logged without failing the full scan job, ensuring partial results are always returned.

---

## 4. Technical Stack

### Backend

| Component | Technology |
|---|---|
| Web Framework | FastAPI 0.110+ |
| Runtime | Python 3.11 |
| AWS SDK | boto3 1.34+ |
| Config Management | pydantic-settings (env file + environment variable resolution) |
| Background Jobs | FastAPI BackgroundTasks |
| Logging | Python `logging` with JSON formatter |
| Tests | pytest + moto (AWS mocking) |

### Frontend

| Component | Technology |
|---|---|
| Framework | React 18 with JSX |
| Build Tool | Vite |
| HTTP Client | Axios with request/response interceptors |
| Icons | lucide-react |
| Routing | react-router-dom v6 |
| Styling | Vanilla CSS with CSS custom properties (dark-mode-capable design system) |

### Infrastructure

| Component | Technology |
|---|---|
| Containerization | Docker (multi-stage builds for frontend, Python slim for backend) |
| Reverse Proxy | Nginx (frontend → API proxy at `/api/v1`) |
| Orchestration | Docker Compose (local), adaptable to ECS / Kubernetes |

### AWS Services Used

- **EC2** — `describe_instances`, `describe_volumes`, `describe_addresses`, `describe_snapshots`
- **S3** — `list_buckets`, `get_bucket_lifecycle_configuration`, `get_bucket_encryption`, `get_bucket_versioning`, `get_public_access_block`
- **RDS** — `describe_db_instances`
- **CloudWatch** — `get_metric_statistics` (CPUUtilization, BucketSizeBytes, NumberOfObjects)
- **Cost Explorer** — `get_cost_and_usage` (SERVICE × REGION grouping, UnblendedCost)

---

## 5. Governance & Policy Model

### Rule Structure

Rules are implemented as pure Python functions that accept a normalized resource dictionary and return a list of violation objects. Each rule function is stateless, deterministic, and independently testable.

```python
# Example violation shape
{
    "rule_id":              "EBS-001",
    "severity":             "HIGH",
    "message":              "EBS volume vol-0abc123 (100GB) is unattached. Estimated waste: $10.00/month.",
    "recommendation":       "Snapshot and delete unattached volumes. Consider lifecycle policies.",
    "compliance_framework": "FinOps",
    "resource_id":          "vol-0abc123",
    "resource_type":        "EBS",
    "region":               "us-east-1"
}
```

### Severity Classification

| Severity | Criteria |
|---|---|
| CRITICAL | Security posture violation (unencrypted storage, public S3 access) |
| HIGH | Active cost waste or idle resource incurring charges |
| MEDIUM | Suboptimal configuration with cost or reliability implications |
| LOW | Missing best practices (tags, versioning, gp2 volume type) |

### Scoring Logic

Risk scores are computed by `scoring.py` using a weighted sum of violation severities:

```
CRITICAL = 40 points  ·  HIGH = 25 points  ·  MEDIUM = 10 points  ·  LOW = 5 points
```

The score is capped at 100 and mapped to a severity band shown on each resource row in the dashboard.

### Extensibility Model

Adding a new rule requires:
1. Adding a rule function to the appropriate rules module (`ec2_rules.py` or `storage_rules.py`)
2. Returning a properly structured violation dict
3. No changes to the scanner, API, or frontend are required

New resource types require a new scanner module and a corresponding entry in the `SCANNERS` registry in `audit.py`. The rules engine is invoked automatically for any type registered there.

---

## 6. Cost Optimization Strategy

### Idle Resource Detection

**EC2:** Instances with 7-day average CPU < 5% are flagged as idle (rule EC2-002). Stopped instances are flagged for EBS cost accumulation (rule EC2-001).

**EBS:** Volumes in `available` state (detached from any instance) are flagged with an estimated cost of `$0.10/GB/month` (rule EBS-001).

**EIP:** Unassociated Elastic IPs are flagged at `~$3.60/month` each (rule EIP-001), matching current AWS pricing for idle EIPs.

**S3:** Buckets with no measurable CloudWatch activity for 90+ days are flagged as idle (rule S3-005). Estimated storage cost is surfaced from the size reported via CloudWatch.

**Snapshots:** Snapshots older than 30 days not linked to any AMI are considered orphaned and flagged with an estimated cost of `$0.05/GB/month` (rule SNAP-001).

### Over-Provisioned Instance Detection

EC2 instances are evaluated against a rightsizing map that suggests a one-size-down replacement for common instance families (m5, m6i, c5, c6i, r5, t3). Downsize suggestions trigger when CPU utilization remains below 20% on an instance type that has a smaller alternative (rule EC2-005). The estimated saving is communicated as part of the violation recommendation.

### Storage Optimization

EBS volumes using `gp2` volume type are flagged for migration to `gp3`, which provides ~20% lower cost and higher baseline throughput with no data migration required and zero downtime (rule EBS-003).

S3 buckets without lifecycle policies are flagged (rule S3-004), as unmanaged buckets will accumulate objects indefinitely, growing storage costs without bound.

### Cost Anomaly Detection

Month-to-date cost is compared against a service breakdown to identify the top cost drivers. The current implementation surfaces top-5 services by spend and per-region distributions. Trend-based anomaly detection (week-over-week deviation) is planned for Phase 2.

---

## 7. Remediation Philosophy

### Safe-Mode Execution

The platform operates in audit-only mode by default. No AWS resources are modified at any stage of the scan or rules evaluation. All remediation output is advisory: structured recommendations attached to each violation, designed to be consumed by operators or downstream automation.

This is an intentional design decision. In production environments, automated deletion of cloud resources without approval gates introduces operational risk that outweighs the efficiency benefit.

### Approval Workflow

The current architecture does not include an automated execution layer. Remediation is communicated as structured violation data via the API. Integration with ticketing systems (Jira, ServiceNow), Slack channels, or runbook automation tools is the expected next layer — consuming the violations endpoint and routing actionable findings to the appropriate team.

### Idempotency Considerations

Scan sessions are independent and keyed by a UUID. Running the same scan twice produces two separate scan sessions. Findings from a completed scan are immutable once written to the store. This guarantees that historical scan data is not overwritten by subsequent runs, which is critical for compliance audit trails.

### Audit Traceability

Every violation is associated with a scan session ID, resource ID, resource type, region, rule ID, and timestamp. The violations API endpoint exposes this full context, making it suitable as input to audit reporting pipelines, SIEM systems, or compliance dashboards.

---

## 8. Observability & Reliability

### Logging Strategy

Structured JSON logging is configured via `app/core/logging.py`. Log events include:

- Scan start and completion with resource and violation counts
- Per-scanner execution with region and resource type
- Cost Explorer API calls and failures
- Rule engine evaluation errors per resource
- API request/response errors

Log level is configurable via `LOG_LEVEL` environment variable. In production, logs are written to stdout for collection by the container runtime (CloudWatch Logs, Datadog, Loki).

### Failure Handling

Scanner failures are isolated per resource type per region. If `scan_eip` fails in `eu-west-1`, the EC2 and EBS scans for the same region continue and complete. Errors are logged with full context and the failed scanner is skipped without failing the entire scan job. Partial results are always returned to the client.

### Rate Limit Handling

The AWS Cost Explorer API has a throttling limit of one request per second. Scanner calls to CloudWatch use single-period requests to minimize API call volume. Boto3 clients are instantiated per-call with credential resolution handled by the factory pattern in `aws_client_factory.py`, allowing credential refresh and region switching without client reinstatiation per scan.

### Retry Logic

Boto3's default retry configuration (standard retry mode, 3 attempts) is inherited. Resource-level errors are caught and logged independently, allowing partial results without cascading failures.

---

## 9. Security Model

### IAM Least Privilege

The scanner requires read-only IAM permissions. No write, delete, or mutating permissions are required or used. The minimum viable IAM policy covers:

```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:DescribeInstances",
    "ec2:DescribeVolumes",
    "ec2:DescribeAddresses",
    "ec2:DescribeSnapshots",
    "ec2:DescribeImages",
    "ec2:DescribeSecurityGroups",
    "rds:DescribeDBInstances",
    "s3:ListAllMyBuckets",
    "s3:GetBucketLifecycleConfiguration",
    "s3:GetBucketVersioning",
    "s3:GetBucketEncryption",
    "s3:GetPublicAccessBlock",
    "s3:GetBucketTagging",
    "cloudwatch:GetMetricStatistics",
    "ce:GetCostAndUsage"
  ],
  "Resource": "*"
}
```

### Credentials Management

AWS credentials are never committed to source control. The platform resolves credentials in the following priority order:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. `.env` file (local development only)
3. IAM instance profile / ECS task role (recommended for production deployments)

In production, the recommended pattern is to attach an IAM role to the compute resource (EC2 instance or ECS task) and avoid static credentials entirely.

### STS AssumeRole

The `aws_role_arn` configuration field enables STS AssumeRole for cross-account scanning. When set, the client factory assumes the specified role before constructing AWS clients. This supports multi-account architectures where the platform runs in a dedicated audit account and assumes roles into target accounts.

### Secrets Management

The settings model (`pydantic-settings`) reads all sensitive values from environment variables or the `.env` file. The `.env` file is listed in `.gitignore` and must never be committed. For production, secrets should be injected via AWS Secrets Manager, Parameter Store, or the native secret management of the deployment platform.

### Frontend Access Controls

The API client includes a Bearer token interceptor. Authentication infrastructure (JWT issuance, validation middleware) is scaffolded and ready for integration with an identity provider. In the current state, the platform is intended for deployment within a private network or behind an authenticated reverse proxy.

---

## 10. Deployment Strategy

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose
- AWS credentials with the permissions listed in the Security Model section

### Local Development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev   # Vite dev server at http://localhost:5173
```

Set `MOCK_AWS=true` in your `.env` to run without real AWS credentials. Mock mode returns representative data for all resource types and enables full UI testing without AWS access.

### Dockerized Deployment

```bash
# Build and start all services
docker-compose up --build

# Services
# Backend  → http://localhost:8000
# Frontend → http://localhost:80  (Nginx proxying /api/v1 to backend)
```

The frontend Nginx configuration proxies all `/api/v1` requests to the FastAPI backend, eliminating CORS complexity in production. The frontend serves a static build from the Nginx container.

### Environment Configuration

Copy `.env.example` to `.env` and populate:

```
APP_ENV=production
MOCK_AWS=false
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
SCAN_REGIONS=us-east-1,us-west-2,ap-south-1
CORS_ORIGINS=https://your-internal-domain.com
```

### Production Deployment Considerations

- Deploy behind an internal load balancer or API gateway — do not expose directly to the internet
- Use IAM roles for compute identity; avoid embedding static credentials in task definitions
- Enable CloudWatch log collection from the backend container
- Consider a persistent backend store (PostgreSQL or DynamoDB) to replace the in-memory session store for multi-instance deployments
- Configure `SCAN_REGIONS` to match the regions actively used by your organization

---

## 11. Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── audit.py          # Scan trigger, resource/violation/cost endpoints
│   │   │       ├── settings.py       # Credential management, mock toggle
│   │   │       └── health.py         # Liveness check
│   │   ├── core/
│   │   │   ├── config.py             # pydantic-settings; all env-driven configuration
│   │   │   ├── store.py              # In-memory session/resource/violation/cost store
│   │   │   └── logging.py            # JSON logging configuration
│   │   ├── services/
│   │   │   ├── scanner/              # One module per AWS resource type
│   │   │   │   ├── ec2_scanner.py
│   │   │   │   ├── ebs_scanner.py
│   │   │   │   ├── eip_scanner.py
│   │   │   │   ├── s3_scanner.py
│   │   │   │   ├── snapshot_scanner.py
│   │   │   │   └── rds_scanner.py
│   │   │   ├── rules_engine/         # Stateless rule evaluation functions
│   │   │   │   ├── ec2_rules.py
│   │   │   │   ├── storage_rules.py
│   │   │   │   └── scoring.py
│   │   │   ├── cost_engine/          # AWS Cost Explorer integration
│   │   │   │   └── cost_explorer.py
│   │   │   └── governance/           # Cross-cutting checks (tags, encryption, SGs)
│   │   │       ├── tag_validation.py
│   │   │       ├── encryption_checks.py
│   │   │       └── security_group_checks.py
│   │   └── utils/
│   │       └── aws_client_factory.py # Centralized boto3 client construction with role support
│   ├── tests/                        # pytest test suite with moto-based AWS mocking
│   ├── scripts/                      # Operational scripts
│   ├── requirements.txt              # Python dependencies (scoped to backend only)
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx         # Main audit interface; all resource/violation/cost views
│   │   │   └── Settings.jsx          # Credential management and scan configuration
│   │   ├── components/
│   │   │   └── Sidebar.jsx           # Navigation chrome
│   │   ├── services/
│   │   │   ├── apiClient.js          # Axios instance with auth and error normalization
│   │   │   └── settingsService.js    # Settings API helpers
│   │   ├── App.jsx                   # Router definition
│   │   └── index.css                 # Design system; CSS custom properties for theming
│   ├── nginx.conf                    # Nginx config with /api/v1 proxy pass to backend
│   ├── vite.config.js
│   └── Dockerfile
│
├── infra/                            # Infrastructure-as-code (extensible)
├── .env.example                      # Reference configuration with documentation
├── docker-compose.yml
└── Makefile                          # Developer workflow automation
```

> **Why is `requirements.txt` inside `backend/` and not at the project root?**
> This is a monorepo with separate `backend/` (Python) and `frontend/` (Node.js) directories. Keeping `requirements.txt` inside `backend/` scopes it to Python dependencies only, avoids conflicts with `package.json`, maps cleanly to Docker `COPY` contexts, and makes the dependency boundary explicit. Any command referencing it should use `backend/requirements.txt` from the project root, or run `pip install -r requirements.txt` from within the `backend/` directory.

---

## 12. Roadmap

### Phase 1 — Core Audit Engine (Current)

- Multi-region resource discovery across EC2, EBS, EIP, S3, Snapshots, RDS
- 10 governance and cost rules with severity classification
- Real-time scan status and results via REST API
- Operational dashboard with resource tables, violations panel, and cost view
- Mock mode for development and demo environments
- Docker Compose deployment

### Phase 2 — Operational Depth

- Persistent storage layer (PostgreSQL) replacing in-memory session store
- Scan history and violation trend tracking across scan sessions
- Cost anomaly detection using week-over-week Cost Explorer data
- Slack and webhook notification integration for new CRITICAL/HIGH findings
- Violation-based waste calculation replacing the estimated percentage model
- CLI export tool for JSON/CSV audit report generation
- Extended EC2 rightsizing using CloudWatch p95 CPU rather than average
- Lambda, CloudFront, and NAT Gateway scanner modules

### Phase 3 — Enterprise-Ready Enhancements

- Multi-account scanning via STS AssumeRole across an AWS Organization
- Role-based access control (RBAC) with account-scoped read permissions
- Policy-as-code: external rule definitions in YAML loaded at runtime without code changes
- Remediation execution layer with approval gates, dry-run mode, and audit log
- Integration with AWS Config for continuous compliance evaluation between scans
- Terraform/CloudFormation drift detection
- Grafana dashboard integration via Prometheus metrics endpoint
- Scheduled scan automation with cron-based triggers and escalation policies
- SOC 2 / CIS Benchmark compliance report generation in PDF format

---

## 13. Why This Project Matters

### What It Demonstrates Professionally

This platform reflects the kind of internal tooling that mature engineering organizations build and maintain when the cost of cloud sprawl becomes operationally significant. It is not a hobby project — it addresses a real and recurring problem in cloud-native environments: the absence of centralized, automated governance over a growing resource inventory.

Building it requires proficiency across a meaningful cross-section of production engineering disciplines:

**Backend systems engineering:** Designing a stateless, horizontally scalable API service with background job processing, structured error handling, and extensible plugin-style scanner and rules architectures.

**AWS platform knowledge:** Working directly with boto3 service APIs, CloudWatch metric retrieval, Cost Explorer API semantics, IAM least-privilege design, and cross-account role assumption — the same APIs used by AWS-native governance products.

**Frontend engineering:** Building a functional operational UI that communicates scan state through polling, renders complex nested data structures across multiple resource types, and gives operators the right signals (severity, risk score, cost impact) at a glance.

**Production operational thinking:** The scan engine isolates failures at the scanner level. Credentials are never committed. Configuration is environment-driven. The platform runs in mock mode for development and can be pointed at a real AWS account with a single environment variable change. These are not afterthoughts — they reflect how real platforms are operated.

**FinOps methodology:** Understanding which AWS cost optimization mechanisms are actually actionable (EIP idle charges, gp2→gp3 migration, stopped instance EBS accumulation) and translating them into detectable, quantifiable signals is a genuine domain skill. This platform codifies that knowledge into reproducible audit logic.

The combination of these capabilities — applied to a real infrastructure problem, delivered with production-oriented architecture — is what distinguishes this project from typical portfolio work.

---

*For environment configuration, see [`.env.example`](./.env.example). For API reference, the FastAPI interactive docs are served at `/docs` when `APP_ENV=development`.*
