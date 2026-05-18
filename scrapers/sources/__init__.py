"""Data source scrapers."""
from scrapers.sources.eol_api import GaokaoScoreScraper, SCHOOL_ID_MAP
from scrapers.sources.sunshine_gaokao import SunshineGaokaoScraper
from scrapers.sources.university_reports import UniversityReportScraper
from scrapers.sources.industry_data import IndustryDataBuilder
from scrapers.sources.scnu_admissions import SCNUAdmissionsScraper
from scrapers.sources.scnu_curriculum import SCNUCurriculumScraper
from scrapers.sources.scnu_employment import SCNUEmploymentScraper

__all__ = [
    "GaokaoScoreScraper",
    "SunshineGaokaoScraper",
    "UniversityReportScraper",
    "IndustryDataBuilder",
    "SCNUAdmissionsScraper",
    "SCNUCurriculumScraper",
    "SCNUEmploymentScraper",
    "SCHOOL_ID_MAP",
]
