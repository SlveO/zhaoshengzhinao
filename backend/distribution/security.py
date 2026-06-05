"""Security utilities for distribution module.

- Fernet encryption for webhook URLs at rest
- File access token generation
- MIME type validation
"""
from __future__ import annotations

import hashlib
import secrets
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from cryptography.fernet import Fernet

from config import settings

# Allowed MIME types for file upload
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", # .pptx
    "application/msword",       # .doc
    "application/vnd.ms-excel", # .xls
    "application/vnd.ms-powerpoint", # .ppt
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/zip",
    "text/plain",
}

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".doc", ".xls", ".ppt",
    ".jpg", ".jpeg", ".png", ".gif",
    ".zip", ".txt",
}

MAX_UPLOAD_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024

_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    """Get or generate a Fernet cipher instance (cached per process)."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    key = settings.webhook_encryption_key
    if not key:
        # In dev, generate a key and warn. In production, this must be set.
        key = Fernet.generate_key().decode()
        print(f"[WARNING] WEBHOOK_ENCRYPTION_KEY not set. Generated ephemeral key (will not survive restart).")
    elif isinstance(key, str):
        key = key.encode()
    _fernet_instance = Fernet(key)
    return _fernet_instance


def encrypt_webhook_url(url: str) -> str:
    """Encrypt a webhook URL for storage in the database."""
    f = _get_fernet()
    return f.encrypt(url.encode()).decode()


def decrypt_webhook_url(encrypted: str) -> str:
    """Decrypt a webhook URL retrieved from the database."""
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


def mask_webhook_url(webhook_url: str) -> str:
    """Mask a webhook URL, showing only the last 4 characters of the key.

    Input:  https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=6b2c3d4e-5f67-8a90-abcd-ef1234567890
    Output: https://qyapi.weixin.qq.com/.../send?key=****7890
    """
    if "?" not in webhook_url:
        return webhook_url[:20] + "****"
    base, params_str = webhook_url.split("?", 1)
    # Extract the key value
    masked_parts = []
    for param in params_str.split("&"):
        if "=" in param:
            k, v = param.split("=", 1)
            if len(v) > 4:
                masked_parts.append(f"{k}={'*' * min(8, len(v) - 4)}{v[-4:]}")
            else:
                masked_parts.append(f"{k}={v}")
        else:
            masked_parts.append(param)
    # Shorten base path
    path_parts = base.split("/")
    if len(path_parts) > 4:
        short_base = "/".join(path_parts[:3]) + "/.../" + path_parts[-1]
    else:
        short_base = base
    return f"{short_base}?{'&'.join(masked_parts)}"


def generate_access_token(file_id: UUID, channel_id: UUID | None = None,
                          expires_in_hours: int = 24) -> str:
    """Generate a cryptographically random file access token."""
    return secrets.token_hex(64)


def validate_file_upload(filename: str, file_size: int, mime_type: str | None = None) -> str | None:
    """Validate file upload. Returns error message string or None if valid.

    Checks: file extension whitelist, MIME type whitelist, file size limit.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"不支持的文件类型: {ext}。支持的类型: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        # Don't block on MIME type alone — some clients send generic types
        pass

    if file_size > MAX_UPLOAD_SIZE_BYTES:
        return f"文件大小 ({file_size / 1024 / 1024:.1f}MB) 超过上限 ({settings.max_upload_size_mb}MB)"

    return None


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
