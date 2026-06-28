"""consult_validator 单测 — 后置校验逻辑。

测试契约：
1. validate_response 通过场景：回复数字与 DB 一致
2. mismatch 场景：回复数字与 DB 不一致
3. fabricated 场景：回复中的专业在 DB 中不存在
4. wrong_major 场景：回复数字是其他专业的
5. 回复无数字时返回空 issues
6. 简称映射：'AI' → '人工智能'
"""
import pytest
import pytest_asyncio

from services.consult_validator import validate_response


# 纯单元测试（无 I/O）— 覆盖 conftest.py 的 autouse setup_db，避免连真实 DB
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def test_validate_pass_when_reply_matches_db():
    """回复数字与 DB 一致时返回空 issues。"""
    reply = "人工智能专业 2024 年在广东最低录取分 585，位次 32000"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert issues == []


def test_validate_mismatch_when_reply_rank_differs_from_db():
    """回复位次与 DB 不一致时返回 mismatch issue。"""
    reply = "人工智能专业 2024 年最低位次 45000"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert len(issues) == 1
    assert issues[0].issue_type == "mismatch"
    assert issues[0].metric == "min_rank"
    assert issues[0].value_in_reply == 45000


def test_validate_fabricated_when_major_not_in_db():
    """回复中的专业在 DB 中不存在时返回 fabricated issue。"""
    reply = "软件工程专业 2024 年最低位次 32000"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert len(issues) == 1
    assert issues[0].issue_type == "fabricated"


def test_validate_wrong_major_when_digit_belongs_to_other_major():
    """回复位次是其他专业的（专业错配）时返回 wrong_major issue。"""
    reply = "人工智能专业 2024 年最低位次 50000"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
        {"major_name": "软件工程", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 580, "min_rank": 50000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert len(issues) >= 1
    assert any(i.issue_type == "wrong_major" for i in issues)


def test_validate_returns_empty_when_reply_has_no_numbers():
    """回复中无数字时返回空 issues。"""
    reply = "华南师范大学暂未公开该专业的录取数据"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert issues == []
