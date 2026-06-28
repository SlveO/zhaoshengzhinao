"""Per-tenant reindex lock + in-memory progress tracking.

设计目的：
1. 防止同一 tenant 并发 reindex（会导致 ChromaDB collection 删除/重建冲突）
2. 提供实时进度查询（total / done / status / started_at / error），供前端可视化
3. 进度状态仅在内存中（进程重启即清空），不持久化 — 因为 reindex 是短时操作

线程模型：
- reindex_tenant 是 async 函数，内部同步操作通过 asyncio.to_thread 包装
- _locks 和 _progress 是模块级全局，跨请求共享
- 访问 _progress 用普通 dict 操作（单线程 event loop 下安全）
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

# per-tenant 锁，防止并发 reindex
_locks: dict[str, asyncio.Lock] = {}

# per-tenant 进度状态
_progress: dict[str, "IndexProgress"] = {}


@dataclass
class IndexProgress:
    """单次 reindex 的实时进度。"""

    status: Literal["idle", "running", "completed", "failed"] = "idle"
    total: int = 0
    done: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    triggered_by: str = "manual"  # "manual" | "startup" | "raw_edit"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "total": self.total,
            "done": self.done,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "triggered_by": self.triggered_by,
            # 便于前端直接用百分比渲染
            "percent": (
                round(self.done / self.total * 100, 1) if self.total > 0 else 0
            ),
        }


def get_lock(tenant_slug: str) -> asyncio.Lock:
    """获取（或创建）per-tenant 锁。"""
    if tenant_slug not in _locks:
        _locks[tenant_slug] = asyncio.Lock()
    return _locks[tenant_slug]


def get_progress(tenant_slug: str) -> IndexProgress:
    """获取进度状态（不存在时返回 idle 状态）。"""
    if tenant_slug not in _progress:
        _progress[tenant_slug] = IndexProgress()
    return _progress[tenant_slug]


def set_progress(tenant_slug: str, **kwargs) -> IndexProgress:
    """更新进度状态字段。"""
    p = get_progress(tenant_slug)
    for k, v in kwargs.items():
        if hasattr(p, k):
            setattr(p, k, v)
    return p


def is_running(tenant_slug: str) -> bool:
    """快速查询是否正在索引。"""
    return get_progress(tenant_slug).status == "running"


def all_progress() -> dict[str, dict]:
    """所有 tenant 的进度（用于全局监控）。"""
    return {slug: p.to_dict() for slug, p in _progress.items() if p.status != "idle"}


def reset_progress(tenant_slug: str) -> None:
    """重置进度（主要用于测试）。"""
    _progress.pop(tenant_slug, None)
