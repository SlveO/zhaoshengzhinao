"""WeChat Work (企业微信) group bot webhook service.

Sends messages and files to WeChat Work groups via the bot webhook API.
API docs: https://developer.work.weixin.qq.com/document/path/91770
"""
from __future__ import annotations

import time
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx

WECHAT_WEBHOOK_BASE = "https://qyapi.weixin.qq.com/cgi-bin/webhook"
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 5, 25]  # seconds


def _extract_key(webhook_url: str) -> str:
    """Extract the 'key' parameter from a WeChat webhook URL."""
    parsed = urlparse(webhook_url)
    params = parse_qs(parsed.query)
    return params.get("key", [None])[0]


def _webhook_timeout() -> httpx.Timeout:
    return httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


async def send_text_message(webhook_url: str, content: str) -> dict:
    """Send a text message to a WeChat Work group via webhook.

    Returns the JSON response from WeChat.
    Raises httpx.HTTPError on network failure.
    """
    payload = {
        "msgtype": "text",
        "text": {
            "content": content,
        },
    }
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_webhook_timeout()) as client:
                resp = await client.post(webhook_url, json=payload)
                data = resp.json()
                if data.get("errcode") == 0:
                    return data
                # WeChat returned an error — don't retry
                return data
        except httpx.HTTPError as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF[attempt - 1])
    raise last_error  # type: ignore[misc]


async def send_markdown_message(webhook_url: str, content: str) -> dict:
    """Send a markdown-formatted message to a WeChat Work group."""
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": content,
        },
    }
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_webhook_timeout()) as client:
                resp = await client.post(webhook_url, json=payload)
                data = resp.json()
                if data.get("errcode") == 0:
                    return data
                return data
        except httpx.HTTPError as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF[attempt - 1])
    raise last_error  # type: ignore[misc]


async def upload_file_to_wechat(webhook_url: str, file_path: str) -> str | None:
    """Upload a file to WeChat Work and return the media_id.

    Uses the webhook upload_media endpoint.
    Returns media_id string on success, None on failure.
    """
    key = _extract_key(webhook_url)
    if not key:
        return None

    upload_url = f"{WECHAT_WEBHOOK_BASE}/upload_media?key={key}&type=file"
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_webhook_timeout()) as client:
                with open(file_path, "rb") as f:
                    resp = await client.post(
                        upload_url,
                        files={"media": (file_name, f, "application/octet-stream")},
                    )
                data = resp.json()
                if data.get("errcode") == 0:
                    return data.get("media_id")
                return None  # WeChat error — don't retry
        except (httpx.HTTPError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF[attempt - 1])
    return None


async def send_file_message(webhook_url: str, media_id: str) -> dict:
    """Send a file message to a WeChat Work group using a media_id."""
    payload = {
        "msgtype": "file",
        "file": {
            "media_id": media_id,
        },
    }
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_webhook_timeout()) as client:
                resp = await client.post(webhook_url, json=payload)
                data = resp.json()
                if data.get("errcode") == 0:
                    return data
                return data
        except httpx.HTTPError as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF[attempt - 1])
    raise last_error  # type: ignore[misc]


async def send_file_to_wechat_group(webhook_url: str, file_path: str,
                                    caption: str | None = None) -> dict:
    """Full flow: optionally send caption → upload file → send file.

    Returns a dict with the overall result.
    """
    result = {"text": None, "file": None, "error": None}

    try:
        # Step 1: Send caption text if provided
        if caption:
            result["text"] = await send_text_message(webhook_url, caption)

        # Step 2: Upload file to WeChat
        media_id = await upload_file_to_wechat(webhook_url, file_path)
        if not media_id:
            result["error"] = "文件上传失败：未能获取 media_id"
            return result

        # Step 3: Send file message
        result["file"] = await send_file_message(webhook_url, media_id)
        if result["file"].get("errcode") != 0:
            result["error"] = f"文件发送失败: {result['file'].get('errmsg', '未知错误')}"

    except httpx.HTTPError as e:
        result["error"] = f"网络错误: {e}"
    except Exception as e:
        result["error"] = f"未知错误: {e}"

    return result


async def test_webhook(webhook_url: str) -> dict:
    """Send a test message to verify the webhook is working.

    Returns {"ok": True} on success, {"ok": False, "error": "..."} on failure.
    """
    try:
        resp = await send_text_message(webhook_url, "这是一条来自招生智脑的测试消息")
        if resp.get("errcode") == 0:
            return {"ok": True}
        else:
            return {"ok": False, "error": resp.get("errmsg", "未知错误")}
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"网络连接失败: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
