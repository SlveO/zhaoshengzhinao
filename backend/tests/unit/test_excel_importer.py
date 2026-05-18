import os
import tempfile
from unittest.mock import AsyncMock, patch

import openpyxl
import pytest

from data.onboarding.excel_importer import import_excel, IMPORT_CONFIG


def _create_test_excel(headers: list[str], rows: list[list]) -> str:
    """Helper: create a temp .xlsx file and return its path."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(tmp.name)
    return tmp.name


class TestImportExcel:
    """Tests for Excel import pipeline: parse → validate → dedup → result."""

    @pytest.mark.asyncio
    async def test_import_valid_admission_rows(self):
        headers = ["year", "province", "batch", "major_name", "min_score",
                    "min_rank", "subject_requirements", "enrollment_quota"]
        rows = [
            [2025, "广东", "本科批", "计算机科学与技术", 589, 28500, "物理", 120],
            [2025, "广东", "本科批", "软件工程", 575, 32000, "物理", 80],
        ]
        tmp_path = _create_test_excel(headers, rows)

        try:
            with patch("data.onboarding.excel_importer.async_session") as mock_session, \
                 patch("data.onboarding.excel_importer.index_tenant_data",
                       new_callable=AsyncMock) as mock_index:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db

                result = await import_excel(
                    tenant_id="t-1", tenant_slug="test",
                    file_path=tmp_path, data_type="admission_score",
                )

                assert result["success"] is True
                assert result["imported"] == 2
                assert len(result["errors"]) == 0
                assert result["total_rows"] == 2
                assert mock_index.call_count == 2
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_missing_columns_rejected(self):
        headers = ["year", "province"]  # missing major_name, min_score, min_rank etc.
        rows = [[2025, "广东"]]
        tmp_path = _create_test_excel(headers, rows)

        try:
            result = await import_excel(
                tenant_id="t-1", tenant_slug="test",
                file_path=tmp_path, data_type="admission_score",
            )
            assert result["success"] is False
            assert "error" in result
            assert "缺少列" in result["error"]
            assert result["imported"] == 0
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_invalid_rows_reported(self):
        headers = ["year", "province", "batch", "major_name", "min_score",
                    "min_rank", "subject_requirements", "enrollment_quota"]
        rows = [
            [2025, "广东", "本科批", "计算机科学", 589, 28500, "物理", 120],  # valid
            [2025, "广东", "本科批", "软件工程", 999, 32000, "物理", 80],     # invalid score
        ]
        tmp_path = _create_test_excel(headers, rows)

        try:
            with patch("data.onboarding.excel_importer.async_session") as mock_session, \
                 patch("data.onboarding.excel_importer.index_tenant_data",
                       new_callable=AsyncMock) as mock_index:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db

                result = await import_excel(
                    tenant_id="t-1", tenant_slug="test",
                    file_path=tmp_path, data_type="admission_score",
                )

                assert result["success"] is True
                assert result["imported"] == 1
                assert len(result["errors"]) == 1
                assert "分数" in result["errors"][0]
                assert result["total_rows"] == 2
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_dedup_skips_duplicates(self):
        headers = ["year", "province", "batch", "major_name", "min_score",
                    "min_rank", "subject_requirements", "enrollment_quota"]
        rows = [
            [2025, "广东", "本科批", "计算机科学", 589, 28500, "物理", 120],
            [2025, "广东", "本科批", "计算机科学", 590, 29000, "物理", 120],  # same year+province+major
        ]
        tmp_path = _create_test_excel(headers, rows)

        try:
            with patch("data.onboarding.excel_importer.async_session") as mock_session, \
                 patch("data.onboarding.excel_importer.index_tenant_data",
                       new_callable=AsyncMock) as mock_index:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db

                result = await import_excel(
                    tenant_id="t-1", tenant_slug="test",
                    file_path=tmp_path, data_type="admission_score",
                )

                assert result["success"] is True
                assert result["imported"] == 1
                assert result["duplicates_skipped"] == 1
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_curriculum_import(self):
        headers = ["major_name", "college", "duration", "core_courses",
                    "objective", "degree"]
        rows = [
            ["计算机科学", "计算机学院", "4年", "数据结构,算法,计组", "培养计算机人才", "工学学士"],
        ]
        tmp_path = _create_test_excel(headers, rows)

        try:
            with patch("data.onboarding.excel_importer.async_session") as mock_session, \
                 patch("data.onboarding.excel_importer.index_tenant_data",
                       new_callable=AsyncMock) as mock_index:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db

                result = await import_excel(
                    tenant_id="t-1", tenant_slug="test",
                    file_path=tmp_path, data_type="curriculum",
                )

                assert result["success"] is True
                assert result["imported"] == 1
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_employment_import(self):
        headers = ["major_name", "year", "employment_rate", "avg_salary",
                    "main_industries", "typical_companies", "further_study_rate"]
        rows = [
            ["计算机科学", 2024, 96.5, 15000, "互联网,金融", "腾讯,阿里", 15.0],
        ]
        tmp_path = _create_test_excel(headers, rows)

        try:
            with patch("data.onboarding.excel_importer.async_session") as mock_session, \
                 patch("data.onboarding.excel_importer.index_tenant_data",
                       new_callable=AsyncMock) as mock_index:
                mock_db = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_db

                result = await import_excel(
                    tenant_id="t-1", tenant_slug="test",
                    file_path=tmp_path, data_type="employment",
                )

                assert result["success"] is True
                assert result["imported"] == 1
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_unknown_data_type_raises(self):
        with pytest.raises(KeyError):
            await import_excel(
                tenant_id="t-1", tenant_slug="test",
                file_path="nonexistent.xlsx", data_type="unknown_type",
            )
