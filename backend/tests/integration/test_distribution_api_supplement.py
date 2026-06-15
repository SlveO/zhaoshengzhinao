"""Supplementary integration tests for distribution API — coverage gaps.

Covers: channel detail/update, file edge cases, task state machine,
log isolation, download flow, unauthorized access.
"""
from __future__ import annotations

import uuid
import pytest_asyncio
import time
from datetime import datetime, timezone, timedelta

import pytest


# ── Auth override ─────────────────────────────────────────────────────

def _fake_user():
    from tenants.models import TenantUser
    return TenantUser(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        user_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        role="admin",
    )


@pytest_asyncio.fixture(autouse=True)
async def _seed_test_user(test_tenant):
    """Create User + TenantUser rows so FK constraints are satisfied."""
    from models import async_session
    from models.user import User
    from tenants.models import TenantUser
    from utils.security import hash_password
    
    async with async_session() as db:
        user = User(
            id=uuid.UUID('33333333-3333-3333-3333-333333333333'),
            username='admin',
            password_hash=hash_password('admin123'),
        )
        await db.merge(user)
        tu = TenantUser(
            id=uuid.UUID('44444444-4444-4444-4444-444444444444'),
            tenant_id=test_tenant.id,
            user_id=uuid.UUID('33333333-3333-3333-3333-333333333333'),
            role='admin',
        )
        await db.merge(tu)
        await db.commit()


@pytest.fixture(autouse=True)
def override_auth(async_client):
    """Auto-override get_current_tenant_user for all distribution tests."""
    from core.tenant_context import get_current_tenant_user
    from main import app
    app.dependency_overrides[get_current_tenant_user] = _fake_user
    yield
    app.dependency_overrides = {}


# ── Helpers ───────────────────────────────────────────────────────────

def _make_webhook_url(key: str) -> str:
    return f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"


async def _create_channel(
    client, name: str = "Test Channel", key: str = "00000000-0000-0000-0000-000000000001"
) -> dict:
    resp = await client.post(
        "/api/v1/distribution/channels",
        json={
            "name": name,
            "channel_type": "wechat_group",
            "webhook_url": _make_webhook_url(key),
        },
        headers={"X-Tenant": "test"},
    )
    return resp.json()


async def _upload_file(
    client, filename: str = "test.pdf", content: bytes = b"pdf-content"
) -> dict:
    resp = await client.post(
        "/api/v1/distribution/files/upload",
        files={"file": (filename, content, "application/pdf")},
        headers={"X-Tenant": "test"},
    )
    return resp.json()


async def _create_task(
    client, file_id: str, channel_id: str, name: str = "Test Task",
    schedule_type: str = "once"
) -> dict:
    resp = await client.post(
        "/api/v1/distribution/tasks",
        json={
            "name": name,
            "file_id": file_id,
            "channel_id": channel_id,
            "schedule_type": schedule_type,
            "message_text": "Hello",
        },
        headers={"X-Tenant": "test"},
    )
    return resp.json()


# ══════════════════════════════════════════════════════════════════════
# Channel detail and update
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_single_channel(async_client, test_tenant):
    """GET /channels/{id} returns 200 with the correct channel."""
    ch = await _create_channel(
        async_client, "Detail Channel", "11111111-0000-0000-0000-000000000001"
    )

    resp = await async_client.get(
        f"/api/v1/distribution/channels/{ch['id']}",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == ch["id"]
    assert data["name"] == "Detail Channel"
    assert "webhook_url_masked" in data
    # Full key must not leak
    assert "11111111-0000-0000-0000-000000000001" not in data["webhook_url_masked"]


@pytest.mark.asyncio
async def test_get_nonexistent_channel(async_client):
    """GET /channels/{id} with a random UUID returns 404."""
    random_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/api/v1/distribution/channels/{random_id}",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_channel(async_client, test_tenant):
    """PUT /channels/{id} updates name and config successfully."""
    ch = await _create_channel(
        async_client, "Before Update", "00000000-0000-0000-0000-000000000002"
    )

    resp = await async_client.put(
        f"/api/v1/distribution/channels/{ch['id']}",
        json={"name": "After Update", "config": {"notify": True}},
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "After Update"
    assert data["config"] == {"notify": True}

    # Verify via GET
    get_resp = await async_client.get(
        f"/api/v1/distribution/channels/{ch['id']}",
        headers={"X-Tenant": "test"},
    )
    assert get_resp.json()["name"] == "After Update"
    assert get_resp.json()["config"] == {"notify": True}


@pytest.mark.asyncio
async def test_update_nonexistent_channel(async_client):
    """PUT /channels/{id} on nonexistent UUID returns 404."""
    random_id = str(uuid.uuid4())
    resp = await async_client.put(
        f"/api/v1/distribution/channels/{random_id}",
        json={"name": "Ghost"},
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# File edge cases
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_upload_oversized_file(async_client):
    """POST /files/upload with file exceeding the size limit returns 400."""
    from distribution import security

    original_max = security.MAX_UPLOAD_SIZE_BYTES
    # Temporarily lower the limit to 10 bytes for deterministic testing
    security.MAX_UPLOAD_SIZE_BYTES = 10

    try:
        content = b"A" * 100  # 100 bytes exceeds 10-byte limit
        resp = await async_client.post(
            "/api/v1/distribution/files/upload",
            files={"file": ("big.pdf", content, "application/pdf")},
            headers={"X-Tenant": "test"},
        )
        assert resp.status_code == 400
        data = resp.json()
        msg = data.get("detail", "")
        assert "超过" in msg or "上限" in msg
    finally:
        security.MAX_UPLOAD_SIZE_BYTES = original_max


@pytest.mark.asyncio
async def test_upload_missing_file(async_client):
    """POST /files/upload without a file field returns 422."""
    resp = await async_client.post(
        "/api/v1/distribution/files/upload",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_nonexistent_file(async_client):
    """DELETE /files/{id} on a nonexistent file returns 404."""
    random_id = str(uuid.uuid4())
    resp = await async_client.delete(
        f"/api/v1/distribution/files/{random_id}",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_file_list_tenant_isolation(
    async_client, test_tenant, other_tenant
):
    """File uploaded under tenant A not visible to tenant B."""
    await _upload_file(async_client, "tenant-a-file.pdf")

    # List as other tenant
    resp = await async_client.get(
        "/api/v1/distribution/files",
        headers={"X-Tenant": "other"},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    filenames = [f["original_filename"] for f in items]
    assert "tenant-a-file.pdf" not in filenames


# ══════════════════════════════════════════════════════════════════════
# Task state machine
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_single_task(async_client, test_tenant):
    """GET /tasks/{id} returns 200 with correct task data."""
    file_data = await _upload_file(async_client)
    ch = await _create_channel(
        async_client, "Task Get Channel", "00000000-0000-0000-0000-000000000003"
    )
    task_data = await _create_task(
        async_client, file_data["id"], ch["id"], "Get Me"
    )

    resp = await async_client.get(
        f"/api/v1/distribution/tasks/{task_data['id']}",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == task_data["id"]
    assert data["name"] == "Get Me"
    assert data["file_name"] is not None
    assert data["channel_name"] is not None


@pytest.mark.asyncio
async def test_update_task(async_client, test_tenant):
    """PUT /tasks/{id} updates name and schedule_type."""
    file_data = await _upload_file(async_client)
    ch = await _create_channel(
        async_client, "Task Update Channel", "00000000-0000-0000-0000-000000000004"
    )
    task_data = await _create_task(
        async_client, file_data["id"], ch["id"], "Before"
    )

    resp = await async_client.put(
        f"/api/v1/distribution/tasks/{task_data['id']}",
        json={"name": "After", "schedule_type": "daily"},
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "After"
    assert data["schedule_type"] == "daily"


@pytest.mark.asyncio
async def test_delete_task(async_client, test_tenant):
    """DELETE /tasks/{id} returns 200, then 404 on re-read."""
    file_data = await _upload_file(async_client)
    ch = await _create_channel(
        async_client, "Task Delete Channel", "00000000-0000-0000-0000-000000000005"
    )
    task_data = await _create_task(
        async_client, file_data["id"], ch["id"], "Delete Me"
    )

    del_resp = await async_client.delete(
        f"/api/v1/distribution/tasks/{task_data['id']}",
        headers={"X-Tenant": "test"},
    )
    assert del_resp.status_code == 200

    # Verify gone
    get_resp = await async_client.get(
        f"/api/v1/distribution/tasks/{task_data['id']}",
        headers={"X-Tenant": "test"},
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_pause_already_paused_task(async_client, test_tenant):
    """POST /tasks/{id}/pause when already paused is idempotent."""
    file_data = await _upload_file(async_client)
    ch = await _create_channel(
        async_client, "DoublePause Channel", "00000000-0000-0000-0000-000000000006"
    )
    task_data = await _create_task(
        async_client, file_data["id"], ch["id"], "Pause Me"
    )

    # First pause
    p1 = await async_client.post(
        f"/api/v1/distribution/tasks/{task_data['id']}/pause",
        headers={"X-Tenant": "test"},
    )
    assert p1.status_code == 200
    assert p1.json()["status"] == "paused"

    # Second pause — idempotent (not 409)
    p2 = await async_client.post(
        f"/api/v1/distribution/tasks/{task_data['id']}/pause",
        headers={"X-Tenant": "test"},
    )
    assert p2.status_code == 200
    assert p2.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_resume_active_task(async_client, test_tenant):
    """POST /tasks/{id}/resume when already active is idempotent."""
    file_data = await _upload_file(async_client)
    ch = await _create_channel(
        async_client, "ResumeActive Channel", "00000000-0000-0000-0000-000000000007"
    )
    task_data = await _create_task(
        async_client, file_data["id"], ch["id"], "Active Me"
    )

    # Task starts as "draft" by default (no scheduled_at).
    # Pause then resume to set to active, then resume again.
    await async_client.post(
        f"/api/v1/distribution/tasks/{task_data['id']}/pause",
        headers={"X-Tenant": "test"},
    )
    r1 = await async_client.post(
        f"/api/v1/distribution/tasks/{task_data['id']}/resume",
        headers={"X-Tenant": "test"},
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "active"

    # Resume again — idempotent
    r2 = await async_client.post(
        f"/api/v1/distribution/tasks/{task_data['id']}/resume",
        headers={"X-Tenant": "test"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "active"


@pytest.mark.asyncio
async def test_run_nonexistent_task(async_client):
    """POST /tasks/{id}/run on nonexistent task returns 404."""
    random_id = str(uuid.uuid4())
    resp = await async_client.post(
        f"/api/v1/distribution/tasks/{random_id}/run",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# Log edge cases
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_logs_tenant_isolation(async_client, test_tenant, other_tenant):
    """Logs from tenant A are not visible to tenant B."""
    file_data = await _upload_file(async_client, "log-isolation.pdf")
    ch = await _create_channel(
        async_client, "LogIso Channel", "00000000-0000-0000-0000-000000000008"
    )

    # Create a task so the FK to distribution_tasks is satisfied
    task_data = await _create_task(
        async_client, file_data["id"], ch["id"], "Log Isolation Task"
    )

    # Manually insert a log entry scoped to the test tenant.
    from models import async_session as _as
    from distribution.models import DistributionLog
    async with _as() as db:
        log = DistributionLog(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            task_id=uuid.UUID(task_data["id"]),
            channel_id=uuid.UUID(ch["id"]),
            file_id=uuid.UUID(file_data["id"]),
            status="success",
            attempt=1,
        )
        db.add(log)
        await db.commit()

    # List logs for test tenant — should have at least 1
    resp_a = await async_client.get(
        "/api/v1/distribution/logs",
        headers={"X-Tenant": "test"},
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["total"] >= 1

    # List logs for other tenant — should be empty
    resp_b = await async_client.get(
        "/api/v1/distribution/logs",
        headers={"X-Tenant": "other"},
    )
    assert resp_b.status_code == 200
    assert resp_b.json()["total"] == 0


# ══════════════════════════════════════════════════════════════════════
# Download flow
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_download_with_valid_token(async_client, test_tenant):
    """GET /files/{id}/download?token=... returns the file bytes."""
    content = b"downloadable content for testing"
    file_data = await _upload_file(async_client, "download-test.pdf", content)

    # Create a valid access token via service layer
    from distribution.service import create_access_token
    token = await create_access_token(
        file_id=uuid.UUID(file_data["id"]),
        expires_in_hours=1,
        max_access=5,
    )

    resp = await async_client.get(
        f"/api/v1/distribution/files/{file_data['id']}/download",
        params={"token": token.token},
    )
    assert resp.status_code == 200
    assert resp.content == content
    assert "application/pdf" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_download_with_invalid_token(async_client, test_tenant):
    """GET /files/{id}/download?token=bad returns 403."""
    file_data = await _upload_file(async_client, "bad-token-test.pdf")

    resp = await async_client.get(
        f"/api/v1/distribution/files/{file_data['id']}/download",
        params={"token": "this-is-a-fake-token-does-not-exist-123"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert "无效" in detail or "过期" in detail


@pytest.mark.asyncio
async def test_download_token_expiry(async_client, test_tenant):
    """Token with very short expiry expires and returns 403."""
    content = b"ephemeral download content"
    file_data = await _upload_file(async_client, "expires-soon.pdf", content)

    from models import async_session as _as
    from distribution.models import DistributionFileAccessToken
    from distribution.security import generate_access_token

    token_str = generate_access_token(uuid.UUID(file_data["id"]))
    # Expires 1 second from now
    expires = datetime.now(timezone.utc) + timedelta(seconds=1)

    async with _as() as db:
        t = DistributionFileAccessToken(
            id=uuid.uuid4(),
            file_id=uuid.UUID(file_data["id"]),
            token=token_str,
            expires_at=expires,
            max_access=5,
        )
        db.add(t)
        await db.commit()

    # Wait past expiry
    time.sleep(1.2)

    resp = await async_client.get(
        f"/api/v1/distribution/files/{file_data['id']}/download",
        params={"token": token_str},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_download_wrong_file_id(async_client, test_tenant):
    """Token valid but file_id in URL differs from token's -> 403."""
    file_data1 = await _upload_file(async_client, "file-one.pdf")
    file_data2 = await _upload_file(async_client, "file-two.pdf")

    from distribution.service import create_access_token
    token = await create_access_token(
        file_id=uuid.UUID(file_data1["id"]),
        expires_in_hours=1,
    )

    # Try downloading file2 with file1's token
    resp = await async_client.get(
        f"/api/v1/distribution/files/{file_data2['id']}/download",
        params={"token": token.token},
    )
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════
# Unauthorized access
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_channel_without_tenant_header(async_client):
    """POST /channels without X-Tenant returns 401."""
    resp = await async_client.post(
        "/api/v1/distribution/channels",
        json={
            "name": "No Tenant",
            "channel_type": "wechat_group",
            "webhook_url": _make_webhook_url("00000000-0000-0000-0000-000000000009"),
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_channels_without_tenant_header(async_client):
    """GET /channels without X-Tenant returns 401."""
    resp = await async_client.get(
        "/api/v1/distribution/channels",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_files_without_tenant_header(async_client):
    """GET /files without X-Tenant returns 401."""
    resp = await async_client.get(
        "/api/v1/distribution/files",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_tasks_without_tenant_header(async_client):
    """GET /tasks without X-Tenant returns 401."""
    resp = await async_client.get(
        "/api/v1/distribution/tasks",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_download_without_token(async_client, test_tenant):
    """GET /files/{id}/download without a token parameter returns 422."""
    file_data = await _upload_file(async_client, "no-token-test.pdf")

    resp = await async_client.get(
        f"/api/v1/distribution/files/{file_data['id']}/download",
    )
    assert resp.status_code in (422, 400)
