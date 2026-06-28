"""recommend_retrieval_service 单元测试。

测试契约（不依赖真实 ChromaDB，mock search_similar）：
- format_rag_context: 空列表返回降级文本
- format_rag_context: 多条目按编号格式化
- format_rag_context: 超长截断
- retrieve_for_chat: 空消息返回空列表
- retrieve_for_chat: 正常调用返回检索结果
- retrieve_for_chat: search_similar 异常时返回空列表
- retrieve_for_recommendations: 无候选时返回空列表
"""
import pytest
from unittest.mock import patch
from services.recommend_retrieval_service import (
    format_rag_context,
    retrieve_for_chat,
    retrieve_for_recommendations,
)


class TestFormatRagContext:
    def test_empty_sources_returns_fallback(self):
        assert format_rag_context([]) == "暂无相关官方信息参考"

    def test_single_source_formatted(self):
        sources = [{"document": "华南师范大学成立于1933年。", "metadata": {"source_title": "学校简介"}}]
        result = format_rag_context(sources)
        assert "1. 学校简介" in result
        assert "华南师范大学成立于1933年。" in result

    def test_multiple_sources_numbered(self):
        sources = [
            {"document": "内容一", "metadata": {"title": "标题一"}},
            {"document": "内容二", "metadata": {"source_title": "标题二"}},
        ]
        result = format_rag_context(sources)
        assert "1. 标题一" in result
        assert "2. 标题二" in result
        assert "内容一" in result
        assert "内容二" in result

    def test_truncation_respects_max_chars(self):
        long_text = "学校介绍" * 200
        sources = [{"document": long_text, "metadata": {"title": "长文本"}}]
        result = format_rag_context(sources, max_chars=100)
        assert len(result) <= 120  # 允许少量超出用于截断符号
        assert "…" in result or len(result) < 100

    def test_empty_document_skipped(self):
        sources = [{"document": "", "metadata": {"title": "空"}}, {"document": "有内容", "metadata": {"title": "有"}}]
        result = format_rag_context(sources)
        assert "有内容" in result
        assert "1. 有" in result  # 空文档跳过后从 1 开始编号


class TestRetrieveForChat:
    @pytest.mark.asyncio
    async def test_empty_content_returns_empty(self):
        result = await retrieve_for_chat("", "scnu", {})
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_content_returns_empty(self):
        result = await retrieve_for_chat("   ", "scnu", {})
        assert result == []

    @pytest.mark.asyncio
    async def test_normal_call_returns_search_results(self):
        mock_results = [{"document": "学校介绍", "metadata": {"title": "简介"}, "distance": 0.5}]
        with patch("services.recommend_retrieval_service.search_similar", return_value=mock_results):
            result = await retrieve_for_chat("学校怎么样", "scnu", {"riasec": {"I": 8, "R": 6}})
        assert result == mock_results

    @pytest.mark.asyncio
    async def test_search_failure_returns_empty(self):
        with patch("services.recommend_retrieval_service.search_similar", side_effect=Exception("DB down")):
            result = await retrieve_for_chat("学校怎么样", "scnu", {})
        assert result == []

    @pytest.mark.asyncio
    async def test_slots_enhance_query(self):
        """画像中的 riasec 和 region 应被加入查询。"""
        captured_query = []
        def mock_search(query, k, tenant_slug):
            captured_query.append(query)
            return []
        with patch("services.recommend_retrieval_service.search_similar", side_effect=mock_search):
            await retrieve_for_chat(
                "学校怎么样",
                "scnu",
                {"riasec": {"I": 8, "A": 7}, "region_pref": {"regions": ["广东", "北京"]}},
            )
        assert len(captured_query) == 1
        assert "学校怎么样" in captured_query[0]
        assert "研究" in captured_query[0] or "设计" in captured_query[0]
        assert "广东" in captured_query[0] or "北京" in captured_query[0]


class TestRetrieveForRecommendations:
    @pytest.mark.asyncio
    async def test_no_candidates_returns_empty(self):
        result = await retrieve_for_recommendations({}, "scnu", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_candidates_focus_query(self):
        candidates = [
            {"metadata": {"college_name": "华南师大", "major_name": "人工智能"}},
            {"metadata": {"college_name": "中山大学", "major_name": "计算机"}},
        ]
        captured_query = []
        def mock_search(query, k, tenant_slug):
            captured_query.append(query)
            return [{"document": "学校介绍", "metadata": {}}]
        with patch("services.recommend_retrieval_service.search_similar", side_effect=mock_search):
            result = await retrieve_for_recommendations(
                profile={"riasec": {"I": 8}},
                tenant_slug="scnu",
                existing_candidates=candidates,
            )
        assert len(result) == 1
        assert "华南师大" in captured_query[0] or "中山大学" in captured_query[0]
        assert "人工智能" in captured_query[0] or "计算机" in captured_query[0]

    @pytest.mark.asyncio
    async def test_search_failure_returns_empty(self):
        with patch("services.recommend_retrieval_service.search_similar", side_effect=Exception("fail")):
            result = await retrieve_for_recommendations(
                profile={},
                tenant_slug="scnu",
                existing_candidates=[{"metadata": {"college_name": "测试"}}],
            )
        assert result == []
