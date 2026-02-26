---
description: Setup and run against a real AWS account
---

## Real AWS Setup Workflow

### Step 1 — Create an IAM User or Role in AWS Console

**Option A: IAM User (quickest)**

1. Go to **AWS Console → IAM → Users → Create user**
2. Name it: `cloud-audit-scanner`
3. Select **"Attach policies directly"** → click **"Create policy"**
4. In the JSON tab, paste the contents of `infra/iam-policy.json`
5. Name the policy: `CloudAuditScannerPolicy` → Create
6. Attach that policy to the user
7. Go to the user → **Security credentials** → **Create access key**
8. Choose **"Application running outside AWS"** → Create
9. **Copy** `Access key ID` and `Secret access key`

**Option B: If you already have `aws configure` set up locally**

Skip to Step 2 and use the AWS Profile method.

---

### Step 2 — Configure your .env

Open `.env` in the project root and fill in:

```env
MOCK_AWS=false
AWS_ACCESS_KEY_ID=AKIA...         # from Step 1
AWS_SECRET_ACCESS_KEY=abc123...   # from Step 1
AWS_REGION=us-east-1
SCAN_REGIONS=us-east-1,us-west-2  # add more regions you use
```

**OR, if using a named AWS profile** (~/.aws/credentials):

```env
MOCK_AWS=false
AWS_PROFILE=my-profile-name
SCAN_REGIONS=us-east-1,us-west-2
```

---

### Step 3 — Enable Cost Explorer (one-time, 24hr wait)

Cost Explorer must be manually enabled the first time.

1. Go to **AWS Console → Billing → Cost Explorer**
2. Click **"Enable Cost Explorer"**
3. Wait **up to 24 hours** for historical data to populate
4. (Optional) Enable **cost anomaly detection** while there

---

### Step 4 — Start the Backend

```bash
cd v:\PlayGround\Cloud_Resource_Audit_and_Cost_Optimization_Platform\backend

# Install deps (first time only)
pip install -r requirements.txt

# Start backend (reads .env automatically)
uvicorn app.main:app --reload --port 8000
```

Verify it started:
```bash
curl http://localhost:8000/health
# → {"status":"healthy","mock_aws":false}
```

---

### Step 5 — Start the Frontend

```bash
cd v:\PlayGround\Cloud_Resource_Audit_and_Cost_Optimization_Platform\frontend

npm install      # first time only
npm run dev      # http://localhost:5173
```

---

### Step 6 — Start PostgreSQL (for persisting scans)

```bash
docker run -d --name cloudaudit-db \
  -p 5432:5432 \
  -e POSTGRES_DB=cloudaudit \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  postgres:16-alpine
```

---

### Step 7 — Run Your First Real Scan

**Via the UI:**
1. Open http://localhost:5173 → click **Scans**
2. Click **"Run New Scan"** → scan starts
3. Wait 30–60 seconds (AWS API calls)
4. Click your scan → see real EC2/EBS/S3/RDS resources
5. Go to **Violations** — see real compliance issues
6. Go to **Cost Analysis** — see your real MTD spend

**Via curl:**
```bash
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Content-Type: application/json" \
  -d '{"regions": ["us-east-1", "us-west-2"]}'
```

**Via API Docs:**
Open http://localhost:8000/docs

---

### What Gets Scanned

| Resource | API Used | What's Checked |
|----------|----------|----------------|
| EC2 instances | `ec2:DescribeInstances` + `cloudwatch:GetMetricStatistics` | Low CPU (<5%), stopped instances, missing tags, open SGs |
| EBS volumes | `ec2:DescribeVolumes` | Unattached volumes, unencrypted volumes |
| S3 buckets | `s3:ListAllMyBuckets` + per-bucket checks | Public access, versioning, encryption, tags |
| RDS instances | `rds:DescribeDBInstances` | Public accessibility, storage encryption, Multi-AZ |
| Cost | `ce:GetCostAndUsage` | MTD spend per service/region, waste estimate |

---

### Troubleshooting

| Error | Fix |
|-------|-----|
| `AccessDenied` on `ce:GetCostAndUsage` | Enable Cost Explorer first (Step 3) |
| `AccessDenied` on any describe call | Check IAM policy is attached to correct user/role |
| `NoRegionError` | Set `AWS_REGION=us-east-1` in .env |
| `InvalidClientTokenId` | Access key might be inactive — rotate it |
| No resources showing | Your account may have no resources in that region |
| Cost shows $0 | Cost Explorer not yet enabled, or <24hrs since first enable |
