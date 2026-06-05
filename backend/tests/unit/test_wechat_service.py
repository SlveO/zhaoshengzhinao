"""Unit tests for WeChat Work webhook service."""
from __future__ import annotations

import pytest


# ── URL Parsing ──────────────────────────────────────────────────────


def test_parse_webhook_key():
    from distribution.wechat_service import _extract_key
    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=6b2c3d4e-5f67-8a90-abcd-ef1234567890"
    key = _extract_key(url)
    assert key == "6b2c3d4e-5f67-8a90-abcd-ef1234567890"


def test_parse_webhook_key_none():
    from distribution.wechat_service import _extract_key
    key = _extract_key("https://example.com/no-key")
    assert key is None


# ── Encryption ───────────────────────────────────────────────────────


def test_encrypt_decrypt_roundtrip():
    from distribution.security import encrypt_webhook_url, decrypt_webhook_url
    original = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key-1234567890abcdef"
    encrypted = encrypt_webhook_url(original)
    # Encrypted should be different from original
    assert encrypted != original
    # Should not contain the raw key
    assert "test-key" not in encrypted
    # Decrypt should recover original
    decrypted = decrypt_webhook_url(encrypted)
    assert decrypted == original


def test_mask_webhook_url():
    from distribution.security import mask_webhook_url
    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=6b2c3d4e-5f67-8a90-abcd-ef1234567890"
    masked = mask_webhook_url(url)
    # Last 4 chars of key should be visible
    assert "7890" in masked
    # Full key should NOT be visible
    assert "6b2c3d4e" not in masked
    # Should have masking characters
    assert "****" in masked or "..." in masked


# ── File Validation ──────────────────────────────────────────────────


def test_validate_file_upload_ok():
    from distribution.security import validate_file_upload
    err = validate_file_upload("test.pdf", 1000, "application/pdf")
    assert err is None


def test_validate_file_upload_bad_extension():
    from distribution.security import validate_file_upload
    err = validate_file_upload("virus.exe", 1000)
    assert err is not None
    assert "不支持" in err


def test_validate_file_upload_too_large():
    from distribution.security import validate_file_upload, MAX_UPLOAD_SIZE_BYTES
    err = validate_file_upload("big.pdf", MAX_UPLOAD_SIZE_BYTES + 1)
    assert err is not None
    assert "超过" in err or "上限" in err


# ── Token Generation ─────────────────────────────────────────────────


def test_generate_access_token():
    from distribution.security import generate_access_token
    import uuid
    file_id = uuid.uuid4()
    token = generate_access_token(file_id)
    # Should be 128 hex chars (64 bytes * 2)
    assert len(token) == 128
    # Should be hex
    assert all(c in "0123456789abcdef" for c in token)


# ── Schemas ──────────────────────────────────────────────────────────


def test_channel_create_valid():
    from distribution.schemas import ChannelCreate
    ch = ChannelCreate(
        name="Test Channel",
        webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc-def-123",
    )
    assert ch.name == "Test Channel"
    assert ch.channel_type == "wechat_group"


def test_channel_create_invalid_webhook():
    from distribution.schemas import ChannelCreate
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        ChannelCreate(
            name="Bad",
            webhook_url="https://evil.com/send",
        )


def test_task_create_valid():
    from distribution.schemas import TaskCreate
    import uuid
    task = TaskCreate(
        name="Test Task",
        file_id=uuid.uuid4(),
        channel_id=uuid.uuid4(),
        schedule_type="daily",
    )
    assert task.name == "Test Task"


def test_task_create_invalid_schedule():
    from distribution.schemas import TaskCreate
    import uuid
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        TaskCreate(
            name="Bad",
            file_id=uuid.uuid4(),
            channel_id=uuid.uuid4(),
            schedule_type="every_minute",  # invalid
        )
