"""Tenant 专业词典加载器 — 从 admission_data 表去重提取专业名。

用于咨询意图提取的专业名标准化：把用户的简称/别名映射到 DB 中的标准专业名。
启动时加载，TTL 10 分钟自动刷新。
"""
import asyncio
import logging
import time
from sqlalchemy import select, distinct

from models import async_session
from models.admission import AdmissionData
from models.college import College

_logger = logging.getLogger(__name__)

# 缓存：tenant_slug → (专业名集合, 加载时间戳)
_CACHE: dict[str, tuple[set[str], float]] = {}
_TTL_SECONDS = 600  # 10 分钟
_LOCK = asyncio.Lock()


async def load_tenant_majors(tenant_slug: str) -> set[str]:
    """加载指定 tenant 的专业名集合（TTL 缓存）。

    Args:
        tenant_slug: 租户 slug

    Returns:
        该租户所有专业名的集合；加载失败返回空集合
    """
    now = time.time()
    cached = _CACHE.get(tenant_slug)
    if cached and (now - cached[1]) < _TTL_SECONDS:
        return cached[0]

    async with _LOCK:
        cached = _CACHE.get(tenant_slug)
        if cached and (now - cached[1]) < _TTL_SECONDS:
            return cached[0]

        majors: set[str] = set()
        try:
            async with async_session() as db:
                from tenants.service import resolve_tenant
                tenant = await resolve_tenant(tenant_slug)
                if not tenant:
                    _logger.warning(f"Tenant not found: {tenant_slug}")
                    return majors

                brand_name = tenant.config.get("brand", {}).get("name", "华南师范大学")
                college_result = await db.execute(
                    select(College).where(College.name == brand_name)
                )
                college = college_result.scalar_one_or_none()
                if not college:
                    _logger.warning(f"College not found for tenant {tenant_slug}: {brand_name}")
                    return majors

                result = await db.execute(
                    select(distinct(AdmissionData.major_name)).where(
                        AdmissionData.college_id == college.id
                    )
                )
                for row in result.scalars():
                    if row:
                        majors.add(row.strip())
        except Exception as e:
            _logger.warning(f"load_tenant_majors failed for {tenant_slug}: {e}")

        _CACHE[tenant_slug] = (majors, time.time())
        _logger.info(f"Loaded {len(majors)} majors for tenant {tenant_slug}")
        return majors


def clear_cache(tenant_slug: str | None = None) -> None:
    """清除缓存（测试用）。"""
    if tenant_slug:
        _CACHE.pop(tenant_slug, None)
    else:
        _CACHE.clear()


# 常见专业简称/别名 → 标准名的映射（硬编码补充，DB 不含别名）
ALIAS_MAP: dict[str, str] = {
    "ai": "人工智能",
    "cs": "计算机科学与技术",
    "ce": "计算机科学与技术",
    "se": "软件工程",
    "软工": "软件工程",
    "计科": "计算机科学与技术",
    "计算机": "计算机科学与技术",
    "网安": "网络空间安全",
    "信安": "信息安全",
    "心理学": "应用心理学",
    "光电": "光电信息科学与工程",
    "数学": "数学与应用数学",
    "物理": "物理学",
    "化学": "化学",
    "生科": "生物科学",
    "地科": "地理科学",
    "思政": "思想政治教育",
    "汉语言": "汉语言文学",
    "英语": "英语",
    "教育学": "教育学",
    "学前": "学前教育",
    "小教": "小学教育",
    "特教": "特殊教育",
    "经管": "经济学",
    "金融": "金融学",
    "会计": "会计学",
    "法学": "法学",
}


def normalize_major(raw: str, dictionary: set[str]) -> str | None:
    """把用户输入的专业名标准化为 DB 中的标准名。

    匹配优先级：
    1. 完全匹配 DB 专业名
    2. 别名表匹配
    3. DB 专业名的子串包含（用户说"人工智能"，DB 有"人工智能"）
    4. 用户输入是 DB 专业名的子串（用户说"计算机"，DB 有"计算机科学与技术"）

    Args:
        raw: 用户输入的专业名（已 strip）
        dictionary: DB 专业名集合

    Returns:
        标准化专业名；无法匹配返回 None
    """
    if not raw:
        return None

    raw = raw.strip()

    # 1. 完全匹配
    if raw in dictionary:
        return raw

    # 2. 别名表
    alias = ALIAS_MAP.get(raw.lower()) or ALIAS_MAP.get(raw)
    if alias and alias in dictionary:
        return alias

    # 3. DB 专业名包含用户输入
    for major in dictionary:
        if raw in major:
            return major

    # 4. 用户输入包含 DB 专业名
    for major in dictionary:
        if major in raw:
            return major

    return None
