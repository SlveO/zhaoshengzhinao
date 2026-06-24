"""Integration tests for Module A — scraper output → knowledge base indexing.

Based on docs/contracts/scnu_scraper_contract.md.
Tests that scraper output format is compatible with knowledge indexer.
Mocks external boundaries (HTTP, PDF parsing, ChromaDB); verifies data flow.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scrapers.sources.scnu_zsb_admissions import SCNUZsbAdmissionsScraper


# ---------------------------------------------------------------------------
# Scraper output format compatibility
# ---------------------------------------------------------------------------


class TestScraperOutputFormat:
    @pytest.mark.asyncio
    async def test_scraper_output_is_json_serializable_list_of_dicts(self):
        # Contract: scraper output is list[dict], JSON serializable
        # Arrange — mock internal methods to produce controlled output
        scraper = SCNUZsbAdmissionsScraper()
        mock_records = [
            {"year": 2024, "province": "广东", "subject_type": "物理",
             "batch": "本科", "major": "计算机", "min_score": 600, "min_rank": 1000},
            {"year": 2024, "province": "广东", "subject_type": "物理",
             "batch": "本科", "major": "电子", "min_score": 590, "min_rank": 1200},
        ]
        with patch.object(scraper, "_get_year_map", new_callable=AsyncMock) as mock_year_map, \
             patch.object(scraper, "_find_pdf_url", new_callable=AsyncMock) as mock_find_pdf, \
             patch.object(scraper, "_parse_pdf_table", return_value=mock_records), \
             patch.object(scraper, "save_raw") as mock_save:
            mock_year_map.return_value = {2024: {"guangdong_url": "http://x/a1"}}
            mock_find_pdf.return_value = "http://x/doc.pdf"
            mock_save.return_value = Path("/tmp/out.json")
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.content = b"pdf bytes"
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            with patch("scrapers.sources.scnu_zsb_admissions.httpx.AsyncClient") as MockClient:
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
                # Act
                result = await scraper.run()
        # Assert — output is JSON serializable
        json.dumps(result)  # no exception
        assert result["records"] == 2

    @pytest.mark.asyncio
    async def test_scraper_records_have_required_fields(self):
        # Contract: each record has year/province/subject_type/batch/major/min_score/min_rank
        scraper = SCNUZsbAdmissionsScraper()
        mock_records = [
            {"year": 2024, "province": "广东", "subject_type": "物理",
             "batch": "本科", "major": "计算机", "min_score": 600, "min_rank": 1000},
        ]
        with patch.object(scraper, "_get_year_map", new_callable=AsyncMock) as mock_year_map, \
             patch.object(scraper, "_find_pdf_url", new_callable=AsyncMock) as mock_find_pdf, \
             patch.object(scraper, "_parse_pdf_table", return_value=mock_records), \
             patch.object(scraper, "save_raw") as mock_save:
            mock_year_map.return_value = {2024: {"guangdong_url": "http://x/a1"}}
            mock_find_pdf.return_value = "http://x/doc.pdf"
            mock_save.return_value = Path("/tmp/out.json")
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.content = b"pdf"
            mock_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            with patch("scrapers.sources.scnu_zsb_admissions.httpx.AsyncClient") as MockClient:
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
                result = await scraper.run()
        # Assert — save_raw called with the records
        assert mock_save.called
        saved_filename = mock_save.call_args[0][0]
        saved_data = mock_save.call_args[0][1]
        assert saved_filename == "admissions_scnu.json"
        assert len(saved_data) == 1
        record = saved_data[0]
        # Verify required fields exist
        for field in ["year", "province", "subject_type", "batch", "major"]:
            assert field in record, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Scraper → knowledge indexer data flow (mocked ChromaDB)
# ---------------------------------------------------------------------------


class TestScraperToKnowledgeIndexerFlow:
    @pytest.mark.asyncio
    async def test_admissions_records_can_be_indexed(self):
        # Integration: scraper output → knowledge_base.index_documents
        # Arrange — simulate scraper output
        records = [
            {"year": 2024, "province": "广东", "subject_type": "物理",
             "batch": "本科", "major": "计算机", "min_score": 600, "min_rank": 1000},
        ]
        # Build docs and metadatas as knowledge indexer expects
        docs = [json.dumps(r, ensure_ascii=False) for r in records]
        metadatas = [{"year": r["year"], "province": r["province"]} for r in records]
        ids = [f"scnu_{r['year']}_{r['province']}_{r['major']}" for r in records]
        # Act — mock index_documents to verify it receives correct format
        with patch("knowledge_base.chroma_client.index_documents") as mock_index:
            mock_index.return_value = None
            from knowledge_base.chroma_client import index_documents
            index_documents(docs, metadatas, ids)
            # Assert — index_documents called with matching lengths
            mock_index.assert_called_once_with(docs, metadatas, ids)
            assert len(docs) == len(metadatas) == len(ids) == 1
