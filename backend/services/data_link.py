"""Core data-link models and pipeline for C-end admissions consultations.

This module owns the pure business flow: append a user/assistant turn, extract
structured student info, merge it into a profile, calculate intent labels, and
refresh tenant-level report statistics. Storage and extraction are injected so
the current JSON mock and later database/LLM integrations can share the same
pipeline.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal, Protocol


StudentIntentLevel = Literal["high", "medium", "low"]
ChatRole = Literal["user", "assistant"]


@dataclass
class ChatMessage:
    id: str
    tenantId: str
    studentId: str
    sessionId: str
    role: ChatRole
    content: str
    createdAt: str


@dataclass
class ChatSession:
    sessionId: str
    tenantId: str
    studentId: str
    messages: list[ChatMessage] = field(default_factory=list)
    startedAt: str = ""
    updatedAt: str = ""


@dataclass
class ExtractedStudentInfo:
    interestedMajors: list[str]
    concerns: list[str]
    rawText: str
    province: str | None = None
    subjectType: str | None = None
    score: int | None = None
    rank: int | None = None
    contactIntent: bool | None = None
    extractor: str = "rule"
    riskPreference: str | None = None
    intentSignals: list[str] = field(default_factory=list)
    summary: str | None = None
    confidence: float | None = None


@dataclass
class StudentProfile:
    studentId: str
    tenantId: str
    interestedMajors: list[str]
    concerns: list[str]
    tags: list[str]
    intentScore: int
    intentLevel: StudentIntentLevel
    consultationCount: int
    firstConsultedAt: str
    lastConsultedAt: str
    province: str | None = None
    subjectType: str | None = None
    score: int | None = None
    rank: int | None = None
    contactIntent: bool = False


@dataclass
class ConsultationReport:
    tenantId: str
    generatedAt: str
    totalStudents: int
    highIntentCount: int
    mediumIntentCount: int
    lowIntentCount: int
    hotMajors: list[dict[str, int | str]]
    hotConcerns: list[dict[str, int | str]]
    provinceDistribution: list[dict[str, int | str]]
    scoreRangeDistribution: list[dict[str, int | str]]


@dataclass
class ProcessConsultationTurnResult:
    session: ChatSession
    extractedInfo: ExtractedStudentInfo
    profile: StudentProfile
    report: ConsultationReport
    extractionMethod: str = "rule"


class DataLinkStore(Protocol):
    def get_session(self, session_id: str) -> ChatSession | None: ...

    def upsert_session(self, session: ChatSession) -> None: ...

    def get_profile(self, tenant_id: str, student_id: str) -> StudentProfile | None: ...

    def upsert_profile(self, profile: StudentProfile) -> None: ...

    def list_profiles(self, tenant_id: str) -> list[StudentProfile]: ...

    def list_sessions(self, tenant_id: str) -> list[ChatSession]: ...

    def save_report(self, report: ConsultationReport) -> None: ...


PROVINCES = [
    "广东",
    "湖南",
    "广西",
    "福建",
    "江西",
    "湖北",
    "河南",
    "河北",
    "山东",
    "山西",
    "江苏",
    "浙江",
    "安徽",
    "四川",
    "重庆",
    "贵州",
    "云南",
    "陕西",
    "甘肃",
    "辽宁",
    "吉林",
    "黑龙江",
    "北京",
    "天津",
    "上海",
    "海南",
    "内蒙古",
    "新疆",
    "西藏",
    "青海",
    "宁夏",
]

SUBJECT_ALIASES = {
    "物理类": ["物理类", "选物理", "物理方向"],
    "历史类": ["历史类", "选历史", "历史方向"],
    "理科": ["理科", "理科生"],
    "文科": ["文科", "文科生"],
}

MAJOR_ALIASES = {
    "人工智能": ["人工智能", "AI", "ai"],
    "软件工程": ["软件工程"],
    "计算机科学与技术": ["计算机科学与技术", "计算机"],
    "数据科学与大数据技术": ["数据科学与大数据技术", "大数据"],
    "电子信息工程": ["电子信息工程", "电子信息"],
    "通信工程": ["通信工程"],
    "网络工程": ["网络工程"],
    "物联网工程": ["物联网工程", "物联网"],
    "自动化": ["自动化"],
    "电气工程": ["电气工程", "电气"],
    "汉语言文学": ["汉语言文学", "中文"],
    "法学": ["法学"],
    "英语": ["英语"],
    "数学": ["数学"],
    "物理学": ["物理学"],
    "化学": ["化学"],
    "生物科学": ["生物科学", "生物"],
    "心理学": ["心理学"],
    "教育学": ["教育学", "教育"],
}

CONCERN_ALIASES = {
    "录取概率": ["录取概率", "稳不稳", "能不能上", "录取机会", "概率"],
    "专业分数线": ["专业分数线", "最低分", "分数线", "往年分数"],
    "就业前景": ["就业前景", "好就业", "就业怎么样", "就业"],
    "宿舍": ["宿舍", "寝室"],
    "学费": ["学费", "收费"],
    "转专业": ["转专业", "换专业"],
    "保研": ["保研", "推免"],
    "考研": ["考研", "升学"],
    "校园环境": ["校园环境", "环境", "校园", "校区"],
    "地理位置": ["地理位置", "位置", "在哪"],
    "招生计划": ["招生计划", "招多少人"],
    "招生群": ["招生群", "QQ群", "微信群"],
    "联系方式": ["联系方式", "电话", "老师微信", "咨询老师", "怎么联系"],
}

CONTACT_KEYWORDS = ["招生群", "联系方式", "电话", "老师微信", "怎么联系", "报名", "QQ群", "微信群"]


def to_plain_dict(value):
    return asdict(value)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extractStudentInfo(text: str) -> ExtractedStudentInfo:
    raw_text = text or ""

    province = next((item for item in PROVINCES if item in raw_text), None)
    subject_type = None
    for normalized, aliases in SUBJECT_ALIASES.items():
        if any(alias in raw_text for alias in aliases):
            subject_type = normalized
            break

    score = _extract_score(raw_text)
    rank = _extract_rank(raw_text)
    majors = _extract_aliases(raw_text, MAJOR_ALIASES)
    concerns = _extract_aliases(raw_text, CONCERN_ALIASES)
    contact_intent = True if any(keyword in raw_text for keyword in CONTACT_KEYWORDS) else None

    return ExtractedStudentInfo(
        province=province,
        subjectType=subject_type,
        score=score,
        rank=rank,
        interestedMajors=majors,
        concerns=concerns,
        contactIntent=contact_intent,
        rawText=raw_text,
    )


def _extract_aliases(text: str, aliases_by_name: dict[str, list[str]]) -> list[str]:
    found: list[str] = []
    lowered = text.lower()
    for normalized, aliases in aliases_by_name.items():
        if any(alias.lower() in lowered for alias in aliases):
            found.append(normalized)
    return _unique(found)


def _extract_score(text: str) -> int | None:
    patterns = [
        r"(?:高考|考了|分数|成绩)?\s*([3-7]\d{2})\s*分",
        r"(?:分数|成绩|高考)\s*[:：]?\s*([3-7]\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _extract_rank(text: str) -> int | None:
    match = re.search(r"(?:位次|排名|排位)\s*[:：]?\s*(\d{3,7})\s*(?:名)?", text)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d{3,7})\s*名", text)
    return int(match.group(1)) if match else None


def updateStudentProfile(
    oldProfile: StudentProfile | None,
    extractedInfo: ExtractedStudentInfo,
    context: dict[str, str],
) -> StudentProfile:
    now = context.get("now") or utc_now_iso()
    if oldProfile is None:
        profile = StudentProfile(
            studentId=context["studentId"],
            tenantId=context["tenantId"],
            province=None,
            subjectType=None,
            score=None,
            rank=None,
            interestedMajors=[],
            concerns=[],
            tags=[],
            intentScore=0,
            intentLevel="low",
            consultationCount=0,
            firstConsultedAt=now,
            lastConsultedAt=now,
            contactIntent=False,
        )
    else:
        profile = oldProfile

    profile.province = extractedInfo.province or profile.province
    profile.subjectType = extractedInfo.subjectType or profile.subjectType
    profile.score = extractedInfo.score if extractedInfo.score is not None else profile.score
    profile.rank = extractedInfo.rank if extractedInfo.rank is not None else profile.rank
    profile.interestedMajors = _unique(profile.interestedMajors + extractedInfo.interestedMajors)
    profile.concerns = _unique(profile.concerns + extractedInfo.concerns)
    profile.contactIntent = profile.contactIntent or bool(extractedInfo.contactIntent)
    profile.consultationCount += 1
    profile.lastConsultedAt = now
    profile.intentScore = calculateIntentScore(profile, extractedInfo)
    profile.intentLevel = getIntentLevel(profile.intentScore)
    profile.tags = generateStudentTags(profile)
    return profile


def calculateIntentScore(
    profile: StudentProfile,
    latestInfo: ExtractedStudentInfo | None = None,
) -> int:
    score = 0
    if profile.score is not None:
        score += 20
    if profile.province:
        score += 10
    if profile.subjectType:
        score += 10
    if profile.interestedMajors:
        score += 20
    concerns = set(profile.concerns)
    if concerns.intersection({"录取概率", "专业分数线"}):
        score += 15
    if profile.consultationCount >= 2:
        score += 10
    contact_intent = profile.contactIntent or bool(latestInfo and latestInfo.contactIntent)
    if contact_intent:
        score += 15
    return max(0, min(score, 100))


def getIntentLevel(score: int) -> StudentIntentLevel:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def generateStudentTags(profile: StudentProfile) -> list[str]:
    tags: list[str] = []
    if profile.province:
        tags.append(f"{profile.province}考生")
    if profile.subjectType:
        tags.append(profile.subjectType)
    if profile.score is not None:
        tags.append(f"{profile.score}分")
    if profile.intentLevel == "high":
        tags.append("高意向")
    elif profile.intentLevel == "medium":
        tags.append("中意向")
    else:
        tags.append("低意向")
    tags.extend([f"关注{major}" for major in profile.interestedMajors])
    tags.extend([f"关注{concern}" for concern in profile.concerns])
    if profile.contactIntent:
        tags.append("有联系意向")
    return _unique(tags)


def generateConsultationReport(
    profiles: list[StudentProfile],
    sessions: list[ChatSession],
    tenantId: str,
) -> ConsultationReport:
    tenant_profiles = [item for item in profiles if item.tenantId == tenantId]
    return ConsultationReport(
        tenantId=tenantId,
        generatedAt=utc_now_iso(),
        totalStudents=len(tenant_profiles),
        highIntentCount=sum(1 for item in tenant_profiles if item.intentLevel == "high"),
        mediumIntentCount=sum(1 for item in tenant_profiles if item.intentLevel == "medium"),
        lowIntentCount=sum(1 for item in tenant_profiles if item.intentLevel == "low"),
        hotMajors=_counter_to_items(_flatten(item.interestedMajors for item in tenant_profiles)),
        hotConcerns=_counter_to_items(_flatten(item.concerns for item in tenant_profiles)),
        provinceDistribution=_counter_to_items(item.province for item in tenant_profiles if item.province),
        scoreRangeDistribution=_score_range_distribution(tenant_profiles),
    )


def _flatten(groups):
    for group in groups:
        for item in group:
            yield item


def _counter_to_items(items) -> list[dict[str, int | str]]:
    counter = Counter(items)
    return [{"name": name, "count": count} for name, count in counter.most_common()]


def _score_range_distribution(profiles: list[StudentProfile]) -> list[dict[str, int | str]]:
    ranges = ["600分以上", "580-599", "560-579", "540-559", "520-539", "500-519", "500分以下", "未知"]
    counter = Counter({name: 0 for name in ranges})
    for profile in profiles:
        score = profile.score
        if score is None:
            key = "未知"
        elif score >= 600:
            key = "600分以上"
        elif score >= 580:
            key = "580-599"
        elif score >= 560:
            key = "560-579"
        elif score >= 540:
            key = "540-559"
        elif score >= 520:
            key = "520-539"
        elif score >= 500:
            key = "500-519"
        else:
            key = "500分以下"
        counter[key] += 1
    return [{"range": name, "count": counter[name]} for name in ranges]


def processConsultationTurn(
    store: DataLinkStore,
    *,
    tenantId: str,
    studentId: str,
    sessionId: str,
    userMessage: str,
    aiReply: str,
    extractor=None,
    now: str | None = None,
) -> ProcessConsultationTurnResult:
    """Process one completed consultation turn after the AI reply is available.

    Call this from the AI consultation layer after it has both ``userMessage``
    and ``aiReply``. The function persists messages through ``store``, uses the
    supplied extractor or the default HybridExtractor, updates the student
    profile, regenerates the report, and returns all updated objects.
    """
    timestamp = now or utc_now_iso()
    session = store.get_session(sessionId)
    if session is None:
        session = ChatSession(
            sessionId=sessionId,
            tenantId=tenantId,
            studentId=studentId,
            messages=[],
            startedAt=timestamp,
            updatedAt=timestamp,
        )

    session.messages.append(_message(tenantId, studentId, sessionId, "user", userMessage, timestamp))
    session.messages.append(_message(tenantId, studentId, sessionId, "assistant", aiReply, timestamp))
    session.updatedAt = timestamp
    store.upsert_session(session)

    active_extractor = extractor
    if active_extractor is None:
        from services.data_link_extractors import HybridExtractor

        active_extractor = HybridExtractor()
    extracted = active_extractor.extract(userMessage, aiReply)
    profile = updateStudentProfile(
        store.get_profile(tenantId, studentId),
        extracted,
        {"tenantId": tenantId, "studentId": studentId, "now": timestamp},
    )
    store.upsert_profile(profile)
    report = generateConsultationReport(store.list_profiles(tenantId), store.list_sessions(tenantId), tenantId)
    store.save_report(report)
    return ProcessConsultationTurnResult(
        session=session,
        extractedInfo=extracted,
        profile=profile,
        report=report,
        extractionMethod=extracted.extractor,
    )


def process_consultation_turn(
    *,
    store: DataLinkStore,
    tenant_id: str,
    student_id: str,
    session_id: str,
    user_message: str,
    ai_reply: str,
    extractor=None,
    now: str | None = None,
) -> ProcessConsultationTurnResult:
    """Snake_case wrapper for backend callers that prefer Python naming."""
    return processConsultationTurn(
        store,
        tenantId=tenant_id,
        studentId=student_id,
        sessionId=session_id,
        userMessage=user_message,
        aiReply=ai_reply,
        extractor=extractor,
        now=now,
    )


def _message(
    tenant_id: str,
    student_id: str,
    session_id: str,
    role: ChatRole,
    content: str,
    created_at: str,
) -> ChatMessage:
    return ChatMessage(
        id=f"msg_{uuid.uuid4().hex[:12]}",
        tenantId=tenant_id,
        studentId=student_id,
        sessionId=session_id,
        role=role,
        content=content,
        createdAt=created_at,
    )


def _merge_user_and_ai_info(
    user_info: ExtractedStudentInfo,
    ai_info: ExtractedStudentInfo,
) -> ExtractedStudentInfo:
    return ExtractedStudentInfo(
        province=user_info.province,
        subjectType=user_info.subjectType,
        score=user_info.score,
        rank=user_info.rank,
        interestedMajors=_unique(user_info.interestedMajors + ai_info.interestedMajors),
        concerns=_unique(user_info.concerns + ai_info.concerns),
        contactIntent=user_info.contactIntent or ai_info.contactIntent,
        rawText=user_info.rawText,
        extractor=user_info.extractor,
        riskPreference=user_info.riskPreference,
        intentSignals=_unique(user_info.intentSignals + ai_info.intentSignals),
        summary=user_info.summary,
        confidence=user_info.confidence,
    )
