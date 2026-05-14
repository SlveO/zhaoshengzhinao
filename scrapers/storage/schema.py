"""Pydantic data models for all collected data types."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class College(BaseModel):
    code: str = Field(..., min_length=5, max_length=6, description="教育部院校代码")
    name: str = Field(..., max_length=100)
    type: str = Field(..., description="综合/理工/师范/医药/财经/农林/语言/政法/体育/艺术")
    level: str = Field(..., description="985/211/双一流/省重点/普通本科/民办本科/独立学院/中外合作")
    province: str = "广东"
    city: str
    is_985: bool = False
    is_211: bool = False
    is_double_first: bool = False
    founded_year: Optional[int] = None
    campuses: list[str] = Field(default_factory=list)
    website: str = ""
    admission_url: str = ""
    employment_report_url: str = ""
    key_disciplines: list[str] = Field(default_factory=list)
    intro: str = ""
    ranking_soft_2024: Optional[int] = None
    student_count: Optional[int] = None
    source: str = ""


class Major(BaseModel):
    college_code: str = Field(..., min_length=5, max_length=6)
    major_code: str = Field(..., min_length=6, max_length=6, description="教育部专业代码")
    major_name: str = Field(..., max_length=100)
    category: str = Field(..., description="学科门类: 哲学/经济学/法学/教育学/文学/历史学/理学/工学/农学/医学/管理学/艺术学")
    subcategory: str = Field(default="", description="专业类")
    degree_type: str = ""
    duration: int = 4
    status: str = "active"  # active | discontinued | new
    new_since: Optional[int] = Field(None, description="新增年份(2023-2025)")
    discontinued_since: Optional[int] = Field(None, description="停招年份")
    is_national_first_class: bool = False
    is_provincial_first_class: bool = False
    special_notes: str = ""
    subject_requirements: str = Field(default="", description="典型选科要求")
    source: str = ""


class Admission(BaseModel):
    college_code: str = Field(..., min_length=5, max_length=6)
    major_name: str = Field(..., max_length=100)
    major_group: str = Field(default="", description="专业组名称")
    year: int = Field(..., ge=2020, le=2025)
    province: str = Field(default="广东")
    batch: str = Field(default="本科批")
    subject_requirements: str = Field(default="", description="选科要求")
    plan_count: Optional[int] = None
    min_score: int = Field(..., ge=0, le=750)
    min_rank: Optional[int] = None
    avg_score: Optional[int] = None
    max_score: Optional[int] = None
    low_score: Optional[int] = None
    source_url: str = ""

    @field_validator("source_url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        return v or "https://eea.gd.gov.cn/"


class Employment(BaseModel):
    college_code: str = Field(..., min_length=5, max_length=6)
    major_name: str = Field(..., max_length=100)
    year: int = Field(..., ge=2020, le=2025)
    graduate_count: Optional[int] = None
    employment_rate: Optional[float] = None
    domestic_graduate_rate: Optional[float] = None
    overseas_rate: Optional[float] = None
    direct_employment_rate: Optional[float] = None
    avg_monthly_salary: Optional[float] = None
    median_monthly_salary: Optional[float] = None
    top_industries: list[dict] = Field(default_factory=list)
    top_positions: list[dict] = Field(default_factory=list)
    top_employers: list[str] = Field(default_factory=list)
    satisfaction_rate: Optional[float] = None
    major_match_rate: Optional[float] = None
    source: str = ""


class Industry(BaseModel):
    industry_name: str = Field(..., max_length=100)
    industry_code: str = ""
    year: int = Field(..., ge=2020, le=2025)
    avg_annual_salary: Optional[float] = None
    salary_growth_rate: Optional[float] = None
    employment_demand_index: Optional[float] = Field(None, ge=0, le=5)
    industry_growth_rate: Optional[float] = None
    entry_difficulty: str = "中等"
    popular_positions: list[dict] = Field(default_factory=list)
    career_path: str = ""
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    insider_reviews: list[dict] = Field(default_factory=list)
    related_majors: list[str] = Field(default_factory=list)
    outlook: str = ""
    source: str = ""


class MajorIndustryMapping(BaseModel):
    major_name: str
    primary_industries: list[str] = Field(default_factory=list)
    secondary_industries: list[str] = Field(default_factory=list)
    typical_positions: list[str] = Field(default_factory=list)
    salary_range: dict = Field(default_factory=lambda: {"entry": 0, "mid": 0, "senior": 0})
