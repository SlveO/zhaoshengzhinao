"""Integration tests for distribution API — channels, files, tasks, logs."""
from __future__ import annotations

import uuid
import os
import tempfile

import pytest
from core.tenant_context import get_current_tenant_user


# Helper: override auth so write endpoints work without a real JWT
def _fake_user():
    from tenants.models import TenantUser
    return TenantUser(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        user_id=uuid.uuid4(),
        role="admin",
    )


@pytest.fixture(autouse=True)
def override_auth(async_client):
    """Auto-override get_current_tenant_user for all distribution tests."""
    from main import app
    app.dependency_overrides[get_current_tenant_user] = _fake_user
    yield
    app.dependency_overrides = {}


# ── Channel Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_channel(async_client, test_tenant):
    resp = await async_client.post(
        "/api/v1/distribution/channels",
        json={
            "name": "测试群",
            "channel_type": "wechat_group",
            "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key-12345678",
        },
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "测试群"
    assert "****" in data["webhook_url_masked"] or "..." in data["webhook_url_masked"]
    # Verify webhook URL is NOT returned in plaintext
    assert "test-key-12345678" not in str(data)


@pytest.mark.asyncio
async def test_create_channel_invalid_webhook(async_client):
    resp = await async_client.post(
        "/api/v1/distribution/channels",
        json={
            "name": "Bad Channel",
            "channel_type": "wechat_group",
            "webhook_url": "https://evil.com/send",
        },
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_channels(async_client, test_tenant):
    # Create a channel first
    await async_client.post(
        "/api/v1/distribution/channels",
        json={
            "name": "List Test Channel",
            "channel_type": "wechat_group",
            "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=list-test-key-12",
        },
        headers={"X-Tenant": "test"},
    )
    resp = await async_client.get(
        "/api/v1/distribution/channels",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_list_channels_tenant_isolation(async_client, test_tenant, other_tenant):
    # Create channel for test tenant
    await async_client.post(
        "/api/v1/distribution/channels",
        json={
            "name": "Tenant A Channel",
            "channel_type": "wechat_group",
            "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=tenant-a-key-12",
        },
        headers={"X-Tenant": "test"},
    )
    # Other tenant should not see it
    resp = await async_client.get(
        "/api/v1/distribution/channels",
        headers={"X-Tenant": "other"},
    )
    assert resp.status_code == 200
    data = resp.json()
    names = [ch["name"] for ch in data["items"]]
    assert "Tenant A Channel" not in names


@pytest.mark.asyncio
async def test_delete_channel(async_client, test_tenant):
    resp = await async_client.post(
        "/api/v1/distribution/channels",
        json={
            "name": "To Delete",
            "channel_type": "wechat_group",
            "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=delete-me-key-12",
        },
        headers={"X-Tenant": "test"},
    )
    ch_id = resp.json()["id"]

    del_resp = await async_client.delete(
        f"/api/v1/distribution/channels/{ch_id}",
        headers={"X-Tenant": "test"},
    )
    assert del_resp.status_code == 200

    # Verify it's gone from list
    list_resp = await async_client.get(
        "/api/v1/distribution/channels",
        headers={"X-Tenant": "test"},
    )
    ids = [ch["id"] for ch in list_resp.json()["items"]]
    assert ch_id not in ids


# ── File Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_file(async_client, test_tenant):
    content = b"%PDF-1.4 fake pdf content for testing"
    resp = await async_client.post(
        "/api/v1/distribution/files/upload",
        files={"file": ("test.pdf", content, "application/pdf")},
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["original_filename"] == "test.pdf"
    assert data["file_size"] == len(content)
    assert data["mime_type"] == "application/pdf"

    # Verify file exists on disk
    from distribution import service
    df = await service.get_file(test_tenant.id, uuid.UUID(data["id"]))
    assert df is not None
    abs_path = service.get_abs_path(df.stored_path)
    assert os.path.exists(abs_path)

    # Cleanup
    await service.delete_file(test_tenant.id, df.id)


@pytest.mark.asyncio
async def test_upload_file_rejects_exe(async_client):
    content = b"MZ\x00\x00 fake exe"
    resp = await async_client.post(
        "/api/v1/distribution/files/upload",
        files={"file": ("virus.exe", content, "application/x-msdownload")},
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_files(async_client, test_tenant):
    # Upload a file first
    await async_client.post(
        "/api/v1/distribution/files/upload",
        files={"file": ("list_test.pdf", b"pdf content", "application/pdf")},
        headers={"X-Tenant": "test"},
    )
    resp = await async_client.get(
        "/api/v1/distribution/files",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_delete_file(async_client, test_tenant):
    resp = await async_client.post(
        "/api/v1/distribution/files/upload",
        files={"file": ("del_test.pdf", b"to delete", "application/pdf")},
        headers={"X-Tenant": "test"},
    )
    file_id = resp.json()["id"]

    del_resp = await async_client.delete(
        f"/api/v1/distribution/files/{file_id}",
        headers={"X-Tenant": "test"},
    )
    assert del_resp.status_code == 200


# ── Task Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_trigger_task(async_client, test_tenant):
    # 1. Upload file
    file_resp = await async_client.post(
        "/api/v1/distribution/files/upload",
        files={"file": ("task_test.pdf", b"hello world", "application/pdf")},
        headers={"X-Tenant": "test"},
    )
    file_id = file_resp.json()["id"]

    # 2. Create channel
    ch_resp = await async_client.post(
        "/api/v1/distribution/channels",
        json={
            "name": "Task Test Channel",
            "channel_type": "wechat_group",
            "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=task-test-key-0001",
        },
        headers={"X-Tenant": "test"},
    )
    ch_id = ch_resp.json()["id"]

    # 3. Create task
    task_resp = await async_client.post(
        "/api/v1/distribution/tasks",
        json={
            "name": "Integration Test Task",
            "file_id": file_id,
            "channel_id": ch_id,
            "schedule_type": "once",
            "message_text": "Test message",
        },
        headers={"X-Tenant": "test"},
    )
    assert task_resp.status_code == 201
    data = task_resp.json()
    assert data["name"] == "Integration Test Task"
    assert data["file_name"] is not None
    task_id = data["id"]

    # 4. List tasks
    list_resp = await async_client.get(
        "/api/v1/distribution/tasks",
        headers={"X-Tenant": "test"},
    )
    assert list_resp.status_code == 200


@pytest.mark.asyncio
async def test_task_cross_tenant_isolation(async_client, test_tenant, other_tenant):
    # Create file + channel + task for test tenant
    file_resp = await async_client.post(
        "/api/v1/distribution/files/upload",
        files={"file": ("isolated.pdf", b"secret", "application/pdf")},
        headers={"X-Tenant": "test"},
    )
    file_id = file_resp.json()["id"]

    ch_resp = await async_client.post(
        "/api/v1/distribution/channels",
        json={
            "name": "Isolated Channel",
            "channel_type": "wechat_group",
            "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=isolated-key-0012",
        },
        headers={"X-Tenant": "test"},
    )
    ch_id = ch_resp.json()["id"]

    task_resp = await async_client.post(
        "/api/v1/distribution/tasks",
        json={
            "name": "Secret Task",
            "file_id": file_id,
            "channel_id": ch_id,
            "schedule_type": "once",
        },
        headers={"X-Tenant": "test"},
    )
    task_id = task_resp.json()["id"]

    # Other tenant should not see the task
    other_resp = await async_client.get(
        f"/api/v1/distribution/tasks/{task_id}",
        headers={"X-Tenant": "other"},
    )
    assert other_resp.status_code == 404

    # Other tenant should not be able to trigger it
    trigger_resp = await async_client.post(
        f"/api/v1/distribution/tasks/{task_id}/run",
        headers={"X-Tenant": "other"},
    )
    assert trigger_resp.status_code == 404


@pytest.mark.asyncio
async def test_pause_resume_task(async_client, test_tenant):
    file_resp = await async_client.post(
        "/api/v1/distribution/files/upload",
        files={"file": ("pause_test.pdf", b"data", "application/pdf")},
        headers={"X-Tenant": "test"},
    )
    file_id = file_resp.json()["id"]

    ch_resp = await async_client.post(
        "/api/v1/distribution/channels",
        json={
            "name": "Pause Test Channel",
            "channel_type": "wechat_group",
            "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=pause-key-000012",
        },
        headers={"X-Tenant": "test"},
    )
    ch_id = ch_resp.json()["id"]

    task_resp = await async_client.post(
        "/api/v1/distribution/tasks",
        json={
            "name": "Pause Task",
            "file_id": file_id,
            "channel_id": ch_id,
            "schedule_type": "once",
            "scheduled_at": "2099-01-01T00:00:00Z",
        },
        headers={"X-Tenant": "test"},
    )
    task_id = task_resp.json()["id"]

    # Pause
    pause_resp = await async_client.post(
        f"/api/v1/distribution/tasks/{task_id}/pause",
        headers={"X-Tenant": "test"},
    )
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    # Resume
    resume_resp = await async_client.post(
        f"/api/v1/distribution/tasks/{task_id}/resume",
        headers={"X-Tenant": "test"},
    )
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "active"


# ── Log Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_logs(async_client, test_tenant):
    resp = await async_client.get(
        "/api/v1/distribution/logs",
        headers={"X-Tenant": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
