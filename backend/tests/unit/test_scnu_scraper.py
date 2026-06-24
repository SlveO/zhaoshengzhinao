"""Unit tests for SCNU admissions scraper — contract-driven black-box tests.

Based on docs/contracts/scnu_scraper_contract.md.
Does NOT read implementation code; tests against public interface signatures only.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure scrapers package is importable (project root contains scrapers/)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scrapers.sources.scnu_zsb_admissions import (
    SCNUZsbAdmissionsScraper,
    _extract_pdf_urls,
)


# ---------------------------------------------------------------------------
# _extract_pdf_urls (module-level function)
# ---------------------------------------------------------------------------


class TestExtractPdfUrls:
    def test_html_with_pdf_links_returns_urls(self):
        # Contract 1: HTML with PDF links → returns URL list
        html = '<html><a href="/doc1.pdf">2024</a><a href="/doc2.pdf">2023</a></html>'
        urls = _extract_pdf_urls(html)
        assert isinstance(urls, list)
        assert len(urls) >= 1

    def test_html_without_pdf_links_returns_empty(self):
        # Contract 2: HTML without PDF links → empty list
        html = '<html><a href="/page.html">No PDF</a></html>'
        urls = _extract_pdf_urls(html)
        assert urls == []

    def test_empty_string_returns_empty(self):
        # Contract 3: empty string → empty list
        urls = _extract_pdf_urls("")
        assert urls == []


# ---------------------------------------------------------------------------
# _parse_pdf_table (mocked pdfplumber)
# ---------------------------------------------------------------------------


def _make_mock_pdf_page(rows):
    """Create a mock pdfplumber page with extract_tables returning rows."""
    page = MagicMock()
    page.extract_tables.return_value = [rows]
    return page


def _make_mock_pdf(pages):
    """Create a mock pdfplumber PDF object."""
    pdf = MagicMock()
    pdf.pages = pages
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=None)
    return pdf


class TestParsePdfTable:
    def test_valid_pdf_returns_structured_data(self):
        # Contract 1: valid PDF bytes → structured table data
        # Arrange — mock pdfplumber.open to return a PDF with table rows
        rows = [
            ["14", "广东", "本科", "物理", "计算机", "600", "1000"],
            ["15", "广东", "本科", "物理", "电子", "590", "1200"],
        ]
        mock_pdf = _make_mock_pdf([_make_mock_pdf_page(rows)])
        scraper = SCNUZsbAdmissionsScraper()
        with patch("scrapers.sources.scnu_zsb_admissions.pdfplumber.open", return_value=mock_pdf):
            # Act
            result = scraper._parse_pdf_table(b"fake pdf bytes", 2024, "guangdong")
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2

    def test_pdf_no_tables_returns_empty(self):
        # Contract 2: PDF without tables → empty list
        page = MagicMock()
        page.extract_tables.return_value = []
        mock_pdf = _make_mock_pdf([page])
        scraper = SCNUZsbAdmissionsScraper()
        with patch("scrapers.sources.scnu_zsb_admissions.pdfplumber.open", return_value=mock_pdf):
            result = scraper._parse_pdf_table(b"empty pdf", 2024, "guangdong")
        assert result == []

    def test_corrupted_pdf_returns_empty_no_exception(self):
        # Contract 3: corrupted PDF bytes → empty list, no exception
        scraper = SCNUZsbAdmissionsScraper()
        with patch("scrapers.sources.scnu_zsb_admissions.pdfplumber.open", side_effect=Exception("corrupted")):
            result = scraper._parse_pdf_table(b"corrupted", 2024, "guangdong")
        assert result == []

    def test_total_row_skipped(self):
        # Contract 6: "合 计" row is skipped
        rows = [
            ["14", "广东", "本科", "物理", "计算机", "600", "1000"],
            ["", "合 计", "", "", "", "", ""],
        ]
        mock_pdf = _make_mock_pdf([_make_mock_pdf_page(rows)])
        scraper = SCNUZsbAdmissionsScraper()
        with patch("scrapers.sources.scnu_zsb_admissions.pdfplumber.open", return_value=mock_pdf):
            result = scraper._parse_pdf_table(b"pdf", 2024, "guangdong")
        # Assert — total row skipped, only 1 data record
        assert len(result) == 1


# ---------------------------------------------------------------------------
# run() (mocked httpx + pdfplumber)
# ---------------------------------------------------------------------------


class TestScraperRun:
    @pytest.mark.asyncio
    async def test_successful_scrape_returns_records_and_output(self):
        # Contract 1: success → records > 0, output is file path
        scraper = SCNUZsbAdmissionsScraper()
        # Arrange — mock the internal methods
        with patch.object(scraper, "_get_year_map", new_callable=AsyncMock) as mock_year_map, \
             patch.object(scraper, "_find_pdf_url", new_callable=AsyncMock) as mock_find_pdf, \
             patch.object(scraper, "_parse_pdf_table") as mock_parse, \
             patch.object(scraper, "save_raw") as mock_save:
            mock_year_map.return_value = {2024: {"guangdong_url": "http://x/article1"}}
            mock_find_pdf.return_value = "http://x/doc.pdf"
            mock_parse.return_value = [{"year": 2024, "province": "广东", "score": 600}]
            mock_save.return_value = Path("/tmp/admissions_scnu.json")
            # Mock httpx.AsyncClient
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
        # Assert
        assert result["source"] == "scnu_zsb_admissions"
        assert result["records"] == 1
        assert "output" in result

    @pytest.mark.asyncio
    async def test_all_failures_returns_zero_records_with_errors(self):
        # Contract 2: all network failures → records=0, errors > 0
        scraper = SCNUZsbAdmissionsScraper()
        with patch.object(scraper, "_get_year_map", new_callable=AsyncMock) as mock_year_map, \
             patch.object(scraper, "_find_pdf_url", new_callable=AsyncMock) as mock_find_pdf, \
             patch.object(scraper, "save_raw") as mock_save:
            mock_year_map.return_value = {2024: {"guangdong_url": "http://x/article1"}}
            mock_find_pdf.return_value = None  # no PDF found
            mock_save.return_value = Path("/tmp/err.json")
            mock_client = AsyncMock()
            with patch("scrapers.sources.scnu_zsb_admissions.httpx.AsyncClient") as MockClient:
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
                result = await scraper.run()
        # Assert
        assert result["records"] == 0
        assert result["errors"] > 0

    @pytest.mark.asyncio
    async def test_partial_failure_returns_records_and_errors(self):
        # Contract 3: partial failure → records > 0 AND errors > 0
        scraper = SCNUZsbAdmissionsScraper()
        with patch.object(scraper, "_get_year_map", new_callable=AsyncMock) as mock_year_map, \
             patch.object(scraper, "_find_pdf_url", new_callable=AsyncMock) as mock_find_pdf, \
             patch.object(scraper, "_parse_pdf_table") as mock_parse, \
             patch.object(scraper, "save_raw") as mock_save:
            mock_year_map.return_value = {
                2024: {"guangdong_url": "http://x/a1"},
                2023: {"guangdong_url": "http://x/a2"},
            }
            # First call finds PDF, second doesn't
            mock_find_pdf.side_effect = ["http://x/doc.pdf", None]
            mock_parse.return_value = [{"year": 2024, "province": "广东"}]
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
        # Assert
        assert result["records"] > 0
        assert result["errors"] > 0

    @pytest.mark.asyncio
    async def test_source_field_is_scnu_zsb_admissions(self):
        # Contract 4: source field == "scnu_zsb_admissions"
        scraper = SCNUZsbAdmissionsScraper()
        with patch.object(scraper, "_get_year_map", new_callable=AsyncMock) as mock_year_map, \
             patch.object(scraper, "save_raw") as mock_save:
            mock_year_map.return_value = {}  # no years → empty
            mock_save.return_value = Path("/tmp/empty.json")
            mock_client = AsyncMock()
            with patch("scrapers.sources.scnu_zsb_admissions.httpx.AsyncClient") as MockClient:
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
                result = await scraper.run()
        assert result["source"] == "scnu_zsb_admissions"
