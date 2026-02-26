# Intermediate Upgrade — Task Tracker

> Track implementation progress for the Intermediate (Startup Level) upgrade.
> Status: `[ ]` todo · `[/]` in progress · `[x]` done

---

## Phase 1 — Network Layer (LB + NAT) 🟢
**Goal:** Expand resource coverage to include Load Balancers and NAT Gateways.

### Backend
- [ ] `backend/app/services/scanner/lb_scanner.py`
  - [ ] List ALBs and NLBs via `elbv2` client
  - [ ] Fetch 7-day avg `RequestCount` from CloudWatch
  - [ ] Mock mode with 1–3 random LBs
  - [ ] Fields: `resource_id`, `resource_type=LB`, `lb_type`, `state`, `avg_request_count`, `listener_count`
- [ ] `backend/app/services/scanner/nat_scanner.py`
  - [ ] List NAT Gateways via `ec2` client
  - [ ] Fetch 7-day `BytesOutToDestination` from CloudWatch (`AWS/NATGateway`)
  - [ ] Mock mode with 1–2 NAT GWs
  - [ ] Fields: `resource_id`, `resource_type=NAT`, `state`, `data_transfer_gb`, `vpc_id`
- [ ] `backend/app/services/rules_engine/lb_rules.py`
  - [ ] `LB-001` — avg request count < 10/day → HIGH (likely unused)
  - [ ] `LB-002` — zero listeners → CRITICAL (orphaned LB)
- [ ] `backend/app/services/rules_engine/nat_rules.py`
  - [ ] `NAT-001` — data transfer < 1 GB over 7 days → HIGH (low-use NAT, ~$32/mo fixed)
- [ ] `backend/app/api/routes/audit.py`
  - [ ] Register `LB` and `NAT` in `SCANNERS` dict
  - [ ] Add `lb_rules` and `nat_rules` to evaluation loop

### Frontend
- [ ] `frontend/src/pages/Dashboard.jsx`
  - [ ] Add `LB` and `NAT` entries to `RESOURCE_TABS`
  - [ ] Add `LBTable` component
  - [ ] Add `NATTable` component
  - [ ] Add stat cards for LB and NAT counts

### Verification
- [ ] `pytest backend/tests/ -v` — all existing tests pass
- [ ] Mock scan includes LB and NAT resources
- [ ] Violations triggered: `LB-001`, `LB-002`, `NAT-001`
- [ ] Frontend tabs render with data, no console errors

---

## Phase 2 — EC2 & RDS Intelligence Upgrade 🟡
**Goal:** Add Spot/RI/ASG signals to EC2 and idle/over-provisioned detection to RDS.

### Backend
- [ ] `backend/app/services/scanner/ec2_scanner.py`
  - [ ] Add `in_asg` — check for `aws:autoscaling:groupName` tag
  - [ ] Add `spot_eligible` — flag t3/m5/c5/c6i/r5 families
  - [ ] Add `ri_candidate` — running > 30 days on On-Demand
  - [ ] Add `network_in_gb` + `network_out_gb` from CloudWatch
- [ ] `backend/app/services/scanner/rds_scanner.py`
  - [ ] Add `avg_cpu_percent` from CloudWatch `CPUUtilization`
  - [ ] Add `avg_connections` from CloudWatch `DatabaseConnections`
  - [ ] Add `storage_autoscaling_enabled` from `MaxAllocatedStorage`
- [ ] `backend/app/services/rules_engine/ec2_rules.py`
  - [ ] `EC2-006` — not in ASG (running On-Demand, no ASG tag) → LOW
  - [ ] `EC2-007` — Spot-eligible type, On-Demand, CPU < 40% → MEDIUM + savings hint
  - [ ] `EC2-008` — RI candidate (running > 30d, consistent type) → LOW
- [ ] `backend/app/services/rules_engine/rds_rules.py` *(NEW)*
  - [ ] `RDS-001` — avg connections < 5 over 7 days (idle DB) → HIGH
  - [ ] `RDS-002` — `db.r5.xlarge` or larger + CPU < 20% (over-provisioned) → MEDIUM
  - [ ] `RDS-003` — storage autoscaling not enabled → LOW
- [ ] `backend/app/api/routes/audit.py`
  - [ ] Plug `rds_rules` into evaluation loop for RDS resources

### Frontend
- [ ] `frontend/src/pages/Dashboard.jsx`
  - [ ] EC2 table: add `In ASG`, `Spot Eligible`, `RI Candidate` columns
  - [ ] RDS table: add `CPU %`, `Connections`, `Storage Autoscale` columns

### Verification
- [ ] Mock: instance with no ASG tag → `EC2-006` fires
- [ ] Mock: RDS with 2 avg connections → `RDS-001` fires
- [ ] Severity and recommendations correct
- [ ] UI reflects new fields without breaking existing columns

---

## Phase 3 — Cost Intelligence Upgrade 🟠
**Goal:** Add daily cost trend and cost-per-tag to Cost Explorer output.

### Backend
- [ ] `backend/app/services/cost_engine/cost_explorer.py`
  - [ ] `get_daily_trend(days=14)` — DAILY granularity, returns `[{date, amount}]`
  - [ ] `get_cost_by_tag(tag_key, regions)` — group by tag dimension
  - [ ] `waste_by_service(records, violations)` — estimate waste per service
  - [ ] Extend `build_cost_summary()` to include `daily_trend`, `waste_by_service`
  - [ ] Mock equivalents for all new functions

### Frontend
- [ ] `frontend/src/pages/Dashboard.jsx`
  - [ ] Daily trend SVG sparkline in Costs tab
  - [ ] Waste-by-service breakdown table
  - [ ] Cost-by-tag summary (if tag data available)

### Verification
- [ ] `GET /api/v1/scans/{id}/costs` returns `daily_trend` array
- [ ] Sparkline renders in frontend without layout breaking
- [ ] No noticeable latency increase on scan completion

---

## Phase 4 — Recommendations Engine 🔵
**Goal:** Transform violations into ranked, dollar-estimated savings actions.

### Backend
- [ ] `backend/app/services/recommendations.py` *(NEW)*
  - [ ] Rule → title + description mapping
  - [ ] Rule → savings formula (e.g. EIP-001 = $3.60, EBS-001 = size_gb × $0.10)
  - [ ] Output shape: `{id, category, rule_id, resource_id, title, description, estimated_monthly_savings, confidence, action}`
  - [ ] Sort descending by `estimated_monthly_savings`
- [ ] `backend/app/core/store.py`
  - [ ] Add `scan_recommendations: dict[str, list]`
- [ ] `backend/app/api/routes/audit.py`
  - [ ] Call `generate_recommendations()` after scan completion
  - [ ] Store in `store.scan_recommendations[scan_id]`
  - [ ] Add `GET /api/v1/scans/{scan_id}/recommendations` route

### Frontend
- [ ] `frontend/src/pages/Recommendations.jsx` *(NEW)*
  - [ ] Fetch latest scan recommendations
  - [ ] Total savings card at top
  - [ ] Sortable table: Category, Rule, Resource, Description, Savings, Confidence, Action
  - [ ] Filter by service category
- [ ] `frontend/src/App.jsx` — add `/recommendations` route
- [ ] `frontend/src/components/Sidebar.jsx` — add Recommendations nav link
- [ ] `frontend/src/pages/Dashboard.jsx` — add preview card (top 3 recs, link to page)

### Verification
- [ ] After scan → recommendations stored and non-empty
- [ ] `GET /api/v1/scans/{id}/recommendations` returns valid JSON list
- [ ] Frontend Recommendations page loads, sorts, and filters correctly
- [ ] Dashboard preview card shows top 3 recs

---

## Phase 5 — Historical & Automation Layer 🟣
**Goal:** Production-grade behavior with history and scheduled audits.

### Backend
- [ ] Expose scan history endpoint (already exists — surface in UI)
- [ ] Add scheduled audit: `GET /api/v1/scans/trigger-daily` cron-compatible endpoint
- [ ] Bump version to `2.0.0` in `main.py`
- [ ] *(Optional)* Recommendation status: `OPEN / DISMISSED / ACCEPTED`

### Frontend
- [ ] Scan history dropdown — load previous scan results
- [ ] Show recommendation changes between scans (new/resolved)
- [ ] Highlight trend indicators (more/fewer violations vs. last scan)

### Verification
- [ ] Multiple scans stored and selectable in UI
- [ ] Cron endpoint triggers scan and stores result
- [ ] Recommendations differ correctly across scans

---

## Progress Summary

| Phase | Status | Key Deliverable |
|---|---|---|
| 1 — Network Layer (LB + NAT) | `[ ]` | Audits Compute + Storage + Database + **Network** |
| 2 — EC2 & RDS Intelligence | `[ ]` | Spot/RI/ASG flags, idle DB detection |
| 3 — Cost Intelligence | `[ ]` | FinOps dashboard: daily trends + tag cost |
| 4 — Recommendations Engine | `[ ]` | Ranked savings actions with dollar estimates |
| 5 — Historical & Automation | `[ ]` | Production SaaS behavior |
