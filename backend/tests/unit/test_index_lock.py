"""Unit tests for knowledge.index_lock — per-tenant reindex lock + progress tracking."""
import asyncio
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Ensure backend/ on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from knowledge.index_lock import (
    IndexProgress,
    get_lock,
    get_progress,
    set_progress,
    is_running,
    all_progress,
    reset_progress,
)


# 纯单元测试 — 覆盖 conftest.py 的 autouse setup_db，避免连真实 DB
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.fixture(autouse=True)
def clean_state():
    """每个测试前后清理全局状态。"""
    yield
    # 清理所有 tenant 进度
    for slug in list(all_progress().keys()):
        reset_progress(slug)
    # 也清理 idle 的
    from knowledge import index_lock
    index_lock._progress.clear()
    index_lock._locks.clear()


def test_get_progress_returns_idle_default():
    p = get_progress("nonexistent_tenant")
    assert p.status == "idle"
    assert p.total == 0
    assert p.done == 0
    assert p.started_at is None
    assert p.error is None


def test_set_progress_updates_fields():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    set_progress("scnu", status="running", total=100, started_at=now)
    p = get_progress("scnu")
    assert p.status == "running"
    assert p.total == 100
    assert p.started_at == now


def test_set_progress_ignores_unknown_fields():
    set_progress("scnu", status="running", unknown_field="ignored")
    p = get_progress("scnu")
    assert p.status == "running"
    assert not hasattr(p, "unknown_field")


def test_is_running_false_by_default():
    assert is_running("scnu") is False


def test_is_running_true_when_running():
    set_progress("scnu", status="running")
    assert is_running("scnu") is True


def test_is_running_false_when_completed():
    set_progress("scnu", status="completed")
    assert is_running("scnu") is False


def test_to_dict_includes_percent():
    set_progress("scnu", status="running", total=100, done=50)
    d = get_progress("scnu").to_dict()
    assert d["percent"] == 50.0
    assert d["status"] == "running"
    assert d["total"] == 100
    assert d["done"] == 50


def test_to_dict_percent_zero_when_total_zero():
    set_progress("scnu", status="running", total=0, done=0)
    d = get_progress("scnu").to_dict()
    assert d["percent"] == 0


def test_all_progress_excludes_idle():
    set_progress("scnu", status="running")
    set_progress("other", status="completed")
    set_progress("idle_tenant", status="idle")
    all_p = all_progress()
    assert "scnu" in all_p
    assert "other" in all_p
    assert "idle_tenant" not in all_p


def test_reset_progress_removes_entry():
    set_progress("scnu", status="running")
    reset_progress("scnu")
    assert get_progress("scnu").status == "idle"


def test_get_lock_returns_same_instance_per_tenant():
    lock1 = get_lock("scnu")
    lock2 = get_lock("scnu")
    assert lock1 is lock2


def test_get_lock_returns_different_instances_per_tenant():
    lock1 = get_lock("scnu")
    lock2 = get_lock("other")
    assert lock1 is not lock2


@pytest.mark.asyncio
async def test_lock_prevents_concurrent_access():
    """验证 asyncio.Lock 能阻止并发 acquire。"""
    lock = get_lock("scnu")
    assert not lock.locked()
    await lock.acquire()
    assert lock.locked()
    # 第二次 acquire 应该阻塞
    try:
        await asyncio.wait_for(lock.acquire(), timeout=0.1)
        assert False, "Should have timed out"
    except asyncio.TimeoutError:
        pass
    lock.release()
    assert not lock.locked()


def test_progress_dataclass_defaults():
    p = IndexProgress()
    assert p.status == "idle"
    assert p.triggered_by == "manual"
    assert p.error is None
