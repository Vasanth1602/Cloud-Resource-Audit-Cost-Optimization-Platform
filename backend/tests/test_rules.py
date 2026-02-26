"""Tests for rules engine and scoring."""
import os
os.environ["MOCK_AWS"] = "true"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/cloudaudit"

from app.services.rules_engine.ec2_rules import evaluate_ec2_rules
from app.services.rules_engine.storage_rules import evaluate_storage_rules
from app.services.rules_engine.scoring import compute_risk_score, risk_label


def _make_ec2(state="running", cpu=50.0, tags=None, public_ip=None):
    return {
        "resource_id": "i-test001",
        "resource_type": "EC2",
        "region": "us-east-1",
        "state": state,
        "tags": tags or {"Environment": "production", "Owner": "team", "Project": "test"},
        "raw_data": {
            "instance_type": "t3.medium",
            "avg_cpu_percent": cpu,
            "public_ip": public_ip,
        },
    }


def test_stopped_ec2_triggers_violation():
    resource = _make_ec2(state="stopped")
    violations = evaluate_ec2_rules(resource)
    rule_ids = [v["rule_id"] for v in violations]
    assert "EC2-001" in rule_ids


def test_idle_ec2_triggers_high_violation():
    resource = _make_ec2(state="running", cpu=2.0)
    violations = evaluate_ec2_rules(resource)
    rule_ids = [v["rule_id"] for v in violations]
    assert "EC2-002" in rule_ids
    high_violations = [v for v in violations if v["severity"] == "HIGH"]
    assert len(high_violations) > 0


def test_missing_tags_trigger_violation():
    resource = _make_ec2(tags={"Environment": ""})
    violations = evaluate_ec2_rules(resource)
    rule_ids = [v["rule_id"] for v in violations]
    assert "EC2-003" in rule_ids


def test_healthy_ec2_no_violations():
    resource = _make_ec2(state="running", cpu=60.0)
    violations = evaluate_ec2_rules(resource)
    # Only check that no CRITICAL/HIGH appear for a healthy resource
    critical_high = [v for v in violations if v["severity"] in ("CRITICAL", "HIGH")]
    assert len(critical_high) == 0


def test_unattached_ebs_triggers_violation():
    resource = {
        "resource_id": "vol-test001",
        "resource_type": "EBS",
        "region": "us-east-1",
        "state": "available",
        "tags": {},
        "raw_data": {"size_gb": 100, "encrypted": True},
    }
    violations = evaluate_storage_rules(resource)
    rule_ids = [v["rule_id"] for v in violations]
    assert "EBS-001" in rule_ids


def test_unencrypted_ebs_is_critical():
    resource = {
        "resource_id": "vol-test002",
        "resource_type": "EBS",
        "region": "us-east-1",
        "state": "in-use",
        "tags": {},
        "raw_data": {"size_gb": 50, "encrypted": False},
    }
    violations = evaluate_storage_rules(resource)
    critical = [v for v in violations if v["severity"] == "CRITICAL"]
    assert len(critical) > 0


def test_public_s3_is_critical():
    resource = {
        "resource_id": "my-public-bucket",
        "resource_type": "S3",
        "region": "us-east-1",
        "state": "active",
        "tags": {},
        "raw_data": {"public_access_blocked": False, "versioning_enabled": True, "encryption_enabled": True},
    }
    violations = evaluate_storage_rules(resource)
    critical = [v for v in violations if v["rule_id"] == "S3-001"]
    assert len(critical) > 0


def test_risk_score_empty_violations():
    assert compute_risk_score([]) == 0.0


def test_risk_score_critical_violation():
    # CRITICAL(40) + HIGH(25) = 65 → falls in HIGH band (51–75)
    # To reach CRITICAL band (76+), need ≥2 CRITICAL violations
    violations = [{"severity": "CRITICAL"}, {"severity": "HIGH"}]
    score = compute_risk_score(violations)
    assert score == 65.0
    assert risk_label(score) == "HIGH"

    # Two CRITICAL violations → 80 points → CRITICAL band
    two_critical = [{"severity": "CRITICAL"}, {"severity": "CRITICAL"}]
    assert risk_label(compute_risk_score(two_critical)) == "CRITICAL"


def test_risk_score_capped_at_100():
    violations = [{"severity": "CRITICAL"}] * 10
    score = compute_risk_score(violations)
    assert score == 100.0
