from data.onboarding.validator import validate_admission_row, validate_curriculum_row, validate_employment_row


def test_valid_admission_row_passes():
    row = {"year": 2025, "province": "广东", "major_name": "计科",
           "min_score": 589, "min_rank": 28500}
    assert validate_admission_row(row) is None


def test_missing_required_field():
    row = {"year": 2025, "province": "广东"}  # 缺 major_name
    err = validate_admission_row(row)
    assert err is not None
    assert "major_name" in err


def test_score_out_of_range():
    row = {"year": 2025, "province": "广东", "major_name": "计科",
           "min_score": 999, "min_rank": 28500}
    err = validate_admission_row(row)
    assert err is not None
    assert "分数" in err


def test_rank_must_be_positive():
    row = {"year": 2025, "province": "广东", "major_name": "计科",
           "min_score": 589, "min_rank": 0}
    err = validate_admission_row(row)
    assert err is not None
    assert "位次" in err


def test_year_out_of_range():
    row = {"year": 2019, "province": "广东", "major_name": "计科",
           "min_score": 589, "min_rank": 28500}
    err = validate_admission_row(row)
    assert err is not None
    assert "年份" in err


def test_valid_curriculum_row_passes():
    row = {"major_name": "计算机科学与技术", "core_courses": "数据结构,操作系统,计组"}
    assert validate_curriculum_row(row) is None


def test_curriculum_missing_required():
    row = {"major_name": "计算机科学与技术"}  # 缺 core_courses
    err = validate_curriculum_row(row)
    assert err is not None
    assert "core_courses" in err


def test_valid_employment_row_passes():
    row = {"major_name": "计算机科学与技术", "year": 2024, "employment_rate": 95.5}
    assert validate_employment_row(row) is None


def test_employment_rate_out_of_range():
    row = {"major_name": "计算机科学与技术", "year": 2024, "employment_rate": 105}
    err = validate_employment_row(row)
    assert err is not None
    assert "就业率" in err


def test_employment_missing_required():
    row = {"major_name": "计算机科学与技术"}  # 缺 year, employment_rate
    err = validate_employment_row(row)
    assert err is not None
