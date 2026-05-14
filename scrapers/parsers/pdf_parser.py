"""PDF parser for university employment quality reports."""
import re
from pathlib import Path
from loguru import logger

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    logger.warning("pdfplumber not installed. PDF parsing disabled.")


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    if pdfplumber is None:
        return ""
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
    except Exception as e:
        logger.error(f"PDF extraction failed for {pdf_path}: {e}")
    return "\n".join(text_parts)


def parse_employment_rate(text: str) -> float | None:
    """Extract overall employment rate percentage from text."""
    patterns = [
        r"毕业生总体就业率[：:是为]\s*([\d.]+)%",
        r"总体毕业去向落实率[：:是为]\s*([\d.]+)%",
        r"就业率[：:是为]\s*([\d.]+)%",
        r"毕业去向落实率[：:是为]\s*([\d.]+)%",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return float(m.group(1)) / 100
    return None


def parse_avg_salary(text: str) -> float | None:
    """Extract average monthly salary from text (in yuan)."""
    patterns = [
        r"平均月薪[入收]?[：:是为]约?\s*([\d,]+\.?\d*)\s*元",
        r"月均收入[：:是为]\s*([\d,]+\.?\d*)\s*元",
        r"平均月收入[：:是为]\s*([\d,]+\.?\d*)\s*元",
        r"月平均工资[：:是为]\s*([\d,]+\.?\d*)\s*元",
        r"平均薪酬[：:是为]\s*([\d,]+\.?\d*)\s*元",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def parse_graduate_rates(text: str) -> dict:
    """Extract domestic graduate / overseas rates."""
    result = {}
    m = re.search(
        r"国内[升学深造]*[读研考研]*\S*率?[：:是为]\s*([\d.]+)%",
        text
    )
    if m:
        result["domestic_graduate_rate"] = float(m.group(1)) / 100

    m = re.search(
        r"出国[出境]*[留学深造]*\S*率?[：:是为]\s*([\d.]+)%",
        text
    )
    if m:
        result["overseas_rate"] = float(m.group(1)) / 100

    return result


def parse_industry_distribution(text: str) -> list[dict]:
    """Extract top industries with percentages."""
    industries = []
    pat = re.findall(
        r"([一-龥a-zA-Z&、/\s]+?(?:服务业|制造业|金融业|教育|"
        r"软件|信息|建筑|批发|交通|房地产|科学研究))"
        r"[\s(（]*(\d+\.?\d*)%",
        text[:3000],
    )
    for name, pct in pat[:5]:
        industries.append({
            "industry": name.strip(),
            "percentage": float(pct) / 100,
        })
    return industries
