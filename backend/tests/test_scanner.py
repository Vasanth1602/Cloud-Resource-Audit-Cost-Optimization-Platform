"""Tests for scanner modules (mock mode)."""
import os
os.environ["MOCK_AWS"] = "true"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/cloudaudit"

from app.services.scanner.ec2_scanner import scan_ec2
from app.services.scanner.ebs_scanner import scan_ebs
from app.services.scanner.s3_scanner import scan_s3
from app.services.scanner.rds_scanner import scan_rds


def test_ec2_scanner_mock_returns_resources():
    results = scan_ec2("us-east-1")
    assert len(results) > 0
    for r in results:
        assert r["resource_type"] == "EC2"
        assert r["resource_id"].startswith("i-")
        assert r["region"] == "us-east-1"
        assert "raw_data" in r
        assert "tags" in r


def test_ebs_scanner_mock_returns_resources():
    results = scan_ebs("us-east-1")
    assert len(results) > 0
    for r in results:
        assert r["resource_type"] == "EBS"
        assert r["resource_id"].startswith("vol-")


def test_s3_scanner_mock_returns_resources():
    results = scan_s3("us-east-1")
    assert len(results) > 0
    for r in results:
        assert r["resource_type"] == "S3"
        assert "raw_data" in r
        assert "public_access_blocked" in r["raw_data"]


def test_rds_scanner_mock_returns_resources():
    results = scan_rds("us-east-1")
    assert len(results) > 0
    for r in results:
        assert r["resource_type"] == "RDS"
        assert "engine" in r["raw_data"]


def test_multi_region_scanning():
    regions = ["us-east-1", "us-west-2"]
    all_resources = []
    for region in regions:
        all_resources.extend(scan_ec2(region))
    assert len(all_resources) > 0
    regions_found = {r["region"] for r in all_resources}
    assert len(regions_found) >= 1
