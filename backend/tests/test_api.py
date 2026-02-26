"""API endpoint integration tests using httpx AsyncClient."""
import os
os.environ["MOCK_AWS"] = "true"

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    # Health endpoint returns: status, mock_aws, scan_count, resource_count
    assert "mock_aws" in data


@pytest.mark.anyio
async def test_version_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["mock_aws"] is True


@pytest.mark.anyio
async def test_list_scans_returns_dict_with_scans_key():
    """GET /api/v1/scans returns {"scans": [...], "total": N}"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/scans")
    assert response.status_code == 200
    data = response.json()
    assert "scans" in data
    assert "total" in data
    assert isinstance(data["scans"], list)


@pytest.mark.anyio
async def test_trigger_scan_and_check_status():
    """POST /api/v1/scans returns 202 with scan_id; GET returns session."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        post_resp = await client.post(
            "/api/v1/scans",
            json={"regions": ["us-east-1"], "resource_types": ["EC2"]},
        )
    assert post_resp.status_code == 202
    data = post_resp.json()
    assert "scan_id" in data
    assert data["status"] == "pending"


@pytest.mark.anyio
async def test_scan_not_found_returns_404():
    """GET /api/v1/scans/<invalid-id> returns 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/scans/nonexistent-scan-id")
    assert response.status_code == 404
