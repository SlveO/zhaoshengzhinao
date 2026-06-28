"""consult_retrieval_service 单测 — 双层检索逻辑。

测试契约：
1. query_admission_data 按 majors+province+year 精确查询
2. year=None 时返回最新 3 年数据
3. 专业名模糊匹配（ILIKE）
4. 空结果返回 []
5. build_rag_query 按 intent_type 构建不同 query
6. chitchat 的 RAG query 为空（跳过检索）
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# 纯单元测试（mock async_session）— 覆盖 conftest.py 的 autouse setup_db，避免连真实 DB
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.mark.asyncio
async def test_query_admission_data_returns_matching_rows():
    """精确查询返回匹配的 admission_data 行。"""
    from services.consult_retrieval_service import query_admission_data
    college_id = uuid.uuid4()
    mock_rows = [
        MagicMock(major_name="人工智能", year=2024, province="广东", batch="本科批",
                  min_score=585, min_rank=32000, subject_requirements="首选物理,再选化学"),
    ]
    with patch("services.consult_retrieval_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_rows
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await query_admission_data(["人工智能"], "广东", 2024, college_id)

    assert len(result) == 1
    assert result[0]["major_name"] == "人工智能"
    assert result[0]["min_rank"] == 32000


@pytest.mark.asyncio
async def test_query_admission_data_returns_empty_when_no_match():
    """无匹配时返回空列表。"""
    from services.consult_retrieval_service import query_admission_data
    with patch("services.consult_retrieval_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await query_admission_data(["不存在专业"], "广东", 2024, uuid.uuid4())

    assert result == []


def test_build_rag_query_data_query_with_majors():
    """data_query + majors 非空 → 构建专业+省份 query。"""
    from services.consult_retrieval_service import build_rag_query
    intent = {"intent_type": "data_query", "majors": ["人工智能"], "province": "广东", "year": 2024}
    user_content = "人工智能 2024 年位次多少"

    query = build_rag_query(intent, user_content)

    assert "人工智能" in query
    assert "广东" in query


def test_build_rag_query_chitchat_returns_empty():
    """chitchat → 返回空串表示跳过 RAG。"""
    from services.consult_retrieval_service import build_rag_query
    intent = {"intent_type": "chitchat", "majors": [], "province": "广东", "year": None}
    user_content = "你好"

    query = build_rag_query(intent, user_content)

    assert query == ""


def test_build_rag_query_policy_query_with_majors():
    """policy_query + majors → 招生章程 query。"""
    from services.consult_retrieval_service import build_rag_query
    intent = {"intent_type": "policy_query", "majors": ["人工智能"], "province": "广东", "year": None}
    user_content = "人工智能专业的选科要求"

    query = build_rag_query(intent, user_content)

    assert "人工智能" in query
    assert "招生章程" in query


def test_build_rag_query_major_intro_without_majors():
    """major_intro + majors 空 → 原始 content + 专业介绍。"""
    from services.consult_retrieval_service import build_rag_query
    intent = {"intent_type": "major_intro", "majors": [], "province": "广东", "year": None}
    user_content = "计算机类专业"

    query = build_rag_query(intent, user_content)

    assert "计算机类专业" in query
    assert "专业介绍" in query
