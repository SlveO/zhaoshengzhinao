from services.data_link import (
    ChatSession,
    ConsultationReport,
    ExtractedStudentInfo,
    StudentProfile,
    calculateIntentScore,
    extractStudentInfo,
    generateConsultationReport,
    generateStudentTags,
    getIntentLevel,
    processConsultationTurn,
    updateStudentProfile,
)
from services.data_link_extractors import HybridExtractor, RuleBasedExtractor
from services.data_link_llm import (
    DataLinkLLMConfig,
    LLMExtractionError,
    LLMExtractor,
    normalize_llm_extracted_info,
    parse_llm_json,
)
from services.data_link_store import JsonDataLinkStore

from tempfile import TemporaryDirectory


class MemoryStore:
    def __init__(self):
        self.sessions = {}
        self.profiles = {}
        self.report = None

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def upsert_session(self, session):
        self.sessions[session.sessionId] = session

    def get_profile(self, tenant_id, student_id):
        return self.profiles.get((tenant_id, student_id))

    def upsert_profile(self, profile):
        self.profiles[(profile.tenantId, profile.studentId)] = profile

    def list_profiles(self, tenant_id=None):
        values = list(self.profiles.values())
        return [item for item in values if item.tenantId == tenant_id] if tenant_id else values

    def list_sessions(self, tenant_id=None):
        values = list(self.sessions.values())
        return [item for item in values if item.tenantId == tenant_id] if tenant_id else values

    def save_report(self, report):
        self.report = report


class FakeLLMClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def complete(self, prompt):
        if self.error:
            raise self.error
        return self.response


class MockExtractor:
    def extract(self, user_message, ai_reply=None):
        return ExtractedStudentInfo(
            province="广东",
            subjectType="物理类",
            score=585,
            rank=None,
            interestedMajors=["人工智能"],
            concerns=["宿舍"],
            contactIntent=None,
            rawText=user_message,
            extractor="llm",
        )


def enabled_llm_config():
    return DataLinkLLMConfig(
        enabled=True,
        provider="deepseek",
        api_key="test-key",
        base_url="https://example.invalid/chat/completions",
        model="deepseek-chat",
        timeout=1,
    )


def test_extract_student_info_recognizes_basic_fields():
    # Arrange
    text = "我是广东物理类考生，585分，位次32000名，想问人工智能稳不稳。"

    # Act
    result = extractStudentInfo(text)

    # Assert
    assert result.province == "广东"
    assert result.subjectType == "物理类"
    assert result.score == 585
    assert result.rank == 32000


def test_extract_student_info_normalizes_major_aliases():
    # Arrange
    text = "我想了解AI、计算机和大数据方向。"

    # Act
    result = extractStudentInfo(text)

    # Assert
    assert "人工智能" in result.interestedMajors
    assert "计算机科学与技术" in result.interestedMajors
    assert "数据科学与大数据技术" in result.interestedMajors


def test_extract_student_info_recognizes_concerns_and_contact_intent():
    # Arrange
    text = "软件工程录取概率怎么样，有招生群或者老师微信吗？"

    # Act
    result = extractStudentInfo(text)

    # Assert
    assert "录取概率" in result.concerns
    assert "招生群" in result.concerns
    assert "联系方式" in result.concerns
    assert result.contactIntent is True


def test_update_student_profile_merges_multi_turn_without_clearing_old_fields():
    # Arrange
    first_info = extractStudentInfo("湖南历史类560分，想了解汉语言文学和宿舍。")
    profile = updateStudentProfile(
        None,
        first_info,
        {"tenantId": "tenant_scnu", "studentId": "stu_001", "now": "2026-06-17T00:00:00Z"},
    )
    second_info = extractStudentInfo("入学后可以转专业吗？")

    # Act
    updated = updateStudentProfile(
        profile,
        second_info,
        {"tenantId": "tenant_scnu", "studentId": "stu_001", "now": "2026-06-17T00:01:00Z"},
    )

    # Assert
    assert updated.province == "湖南"
    assert updated.subjectType == "历史类"
    assert updated.score == 560
    assert "汉语言文学" in updated.interestedMajors
    assert "宿舍" in updated.concerns
    assert "转专业" in updated.concerns
    assert updated.consultationCount == 2


def test_calculate_intent_score_levels_cover_high_medium_low():
    # Arrange
    high = StudentProfile(
        studentId="s1",
        tenantId="t1",
        province="广东",
        subjectType="物理类",
        score=585,
        rank=None,
        interestedMajors=["人工智能"],
        concerns=["录取概率"],
        contactIntent=True,
        tags=[],
        intentScore=0,
        intentLevel="low",
        consultationCount=2,
        firstConsultedAt="2026-06-17T00:00:00Z",
        lastConsultedAt="2026-06-17T00:00:00Z",
    )
    medium = StudentProfile(
        **{
            **high.__dict__,
            "studentId": "s2",
            "concerns": [],
            "contactIntent": False,
            "consultationCount": 1,
        }
    )
    low = StudentProfile(
        studentId="s3",
        tenantId="t1",
        province=None,
        subjectType=None,
        score=None,
        rank=None,
        interestedMajors=[],
        concerns=[],
        contactIntent=False,
        tags=[],
        intentScore=0,
        intentLevel="low",
        consultationCount=1,
        firstConsultedAt="2026-06-17T00:00:00Z",
        lastConsultedAt="2026-06-17T00:00:00Z",
    )

    # Act
    high_score = calculateIntentScore(high)
    medium_score = calculateIntentScore(medium)
    low_score = calculateIntentScore(low)

    # Assert
    assert getIntentLevel(high_score) == "high"
    assert getIntentLevel(medium_score) == "medium"
    assert getIntentLevel(low_score) == "low"


def test_generate_student_tags_builds_readable_labels():
    # Arrange
    profile = StudentProfile(
        studentId="s1",
        tenantId="t1",
        province="广东",
        subjectType="物理类",
        score=585,
        rank=None,
        interestedMajors=["人工智能"],
        concerns=["录取概率"],
        contactIntent=True,
        tags=[],
        intentScore=85,
        intentLevel="high",
        consultationCount=2,
        firstConsultedAt="2026-06-17T00:00:00Z",
        lastConsultedAt="2026-06-17T00:00:00Z",
    )

    # Act
    tags = generateStudentTags(profile)

    # Assert
    assert "广东考生" in tags
    assert "物理类" in tags
    assert "585分" in tags
    assert "高意向" in tags
    assert "关注人工智能" in tags
    assert "有联系意向" in tags


def test_generate_consultation_report_aggregates_dimensions():
    # Arrange
    profiles = [
        StudentProfile(
            studentId="s1",
            tenantId="tenant_scnu",
            province="广东",
            subjectType="物理类",
            score=585,
            rank=None,
            interestedMajors=["人工智能"],
            concerns=["录取概率"],
            contactIntent=False,
            tags=[],
            intentScore=75,
            intentLevel="high",
            consultationCount=2,
            firstConsultedAt="2026-06-17T00:00:00Z",
            lastConsultedAt="2026-06-17T00:00:00Z",
        ),
        StudentProfile(
            studentId="s2",
            tenantId="tenant_scnu",
            province="湖南",
            subjectType="历史类",
            score=560,
            rank=None,
            interestedMajors=["汉语言文学"],
            concerns=["宿舍"],
            contactIntent=False,
            tags=[],
            intentScore=55,
            intentLevel="medium",
            consultationCount=1,
            firstConsultedAt="2026-06-17T00:00:00Z",
            lastConsultedAt="2026-06-17T00:00:00Z",
        ),
    ]

    # Act
    report = generateConsultationReport(profiles, [], "tenant_scnu")

    # Assert
    assert report.totalStudents == 2
    assert report.highIntentCount == 1
    assert {"name": "人工智能", "count": 1} in report.hotMajors
    assert {"name": "录取概率", "count": 1} in report.hotConcerns
    assert {"name": "广东", "count": 1} in report.provinceDistribution
    assert {"range": "580-599", "count": 1} in report.scoreRangeDistribution
    assert {"range": "560-579", "count": 1} in report.scoreRangeDistribution


def test_process_consultation_turn_runs_complete_pipeline():
    # Arrange
    store = MemoryStore()

    # Act
    first = processConsultationTurn(
        store,
        tenantId="tenant_scnu",
        studentId="stu_demo_001",
        sessionId="session_demo_001",
        userMessage="广东物理类585分，想问人工智能稳不稳？",
        aiReply="建议关注人工智能和软件工程，也要看专业分数线。",
        now="2026-06-17T00:00:00Z",
    )
    second = processConsultationTurn(
        store,
        tenantId="tenant_scnu",
        studentId="stu_demo_001",
        sessionId="session_demo_001",
        userMessage="有招生群吗？",
        aiReply="招生群以官方发布为准。",
        now="2026-06-17T00:01:00Z",
    )

    # Assert
    assert isinstance(first.session, ChatSession)
    assert isinstance(second.report, ConsultationReport)
    assert len(second.session.messages) == 4
    assert second.profile.intentLevel == "high"
    assert second.report.totalStudents == 1
    assert store.report.highIntentCount == 1


def test_manual_input_case_keeps_profile_and_merges_new_concerns():
    # Arrange
    store = MemoryStore()

    # Act
    first = processConsultationTurn(
        store,
        tenantId="tenant_scnu",
        studentId="stu_manual_001",
        sessionId="session_manual_001",
        userMessage="我是广东物理类考生，585分，想问人工智能专业稳不稳？",
        aiReply="你的分数有一定竞争力，可以关注人工智能和软件工程。",
        now="2026-06-17T00:00:00Z",
    )
    second = processConsultationTurn(
        store,
        tenantId="tenant_scnu",
        studentId="stu_manual_001",
        sessionId="session_manual_001",
        userMessage="那宿舍怎么样？可以转专业吗？",
        aiReply="学校宿舍条件整体较好，转专业需要满足学院相关要求。",
        now="2026-06-17T00:01:00Z",
    )

    # Assert
    assert first.extractedInfo.province == "广东"
    assert second.profile.province == "广东"
    assert second.profile.subjectType == "物理类"
    assert second.profile.score == 585
    assert "人工智能" in second.profile.interestedMajors
    assert "软件工程" in second.profile.interestedMajors
    assert "录取概率" in second.profile.concerns
    assert "宿舍" in second.profile.concerns
    assert "转专业" in second.profile.concerns
    assert second.profile.consultationCount == 2
    assert second.report.totalStudents == 1


def test_hybrid_extractor_uses_rule_when_api_key_is_missing():
    # Arrange
    extractor = HybridExtractor(rule_extractor=RuleBasedExtractor())
    extractor.config.enabled = True
    extractor.config.api_key = ""

    # Act
    result = extractor.extract("我是广东物理类考生，585分，想问人工智能稳不稳。")

    # Assert
    assert result.extractor == "rule"
    assert result.province == "广东"
    assert result.subjectType == "物理类"
    assert result.score == 585


def test_llm_extractor_parses_standard_json_response():
    # Arrange
    response = """{
      "province": "广东",
      "subjectType": "物理类",
      "score": 585,
      "rank": 32000,
      "interestedMajors": ["人工智能", "软件工程"],
      "concerns": ["录取概率"],
      "riskPreference": "稳妥",
      "intentSignals": ["提供分数"],
      "summary": "广东物理类高意向考生",
      "confidence": 0.92
    }"""
    extractor = LLMExtractor(config=enabled_llm_config(), client=FakeLLMClient(response=response))

    # Act
    result = extractor.extract("我是广东物理类考生，585分。", "可以关注人工智能和软件工程。")

    # Assert
    assert result.extractor == "llm"
    assert result.province == "广东"
    assert result.subjectType == "物理类"
    assert result.score == 585
    assert result.rank == 32000
    assert result.interestedMajors == ["人工智能", "软件工程"]
    assert result.concerns == ["录取概率"]
    assert result.riskPreference == "稳妥"
    assert result.confidence == 0.92


def test_llm_json_parser_accepts_markdown_code_block():
    # Arrange
    response = """```json
    {"province":"湖南","subjectType":"历史类","score":"560","interestedMajors":"汉语言文学","concerns":["宿舍"]}
    ```"""

    # Act
    raw = parse_llm_json(response)
    result = normalize_llm_extracted_info(raw, raw_text="湖南历史类560分")

    # Assert
    assert result.province == "湖南"
    assert result.subjectType == "历史类"
    assert result.score == 560
    assert result.interestedMajors == ["汉语言文学"]
    assert result.concerns == ["宿舍"]


def test_normalize_llm_extracted_info_cleans_mixed_field_types():
    # Arrange
    raw = {
        "province": "广西",
        "subjectType": "物理类",
        "score": "530分",
        "rank": "32000名",
        "interestedMajors": "电子信息、电子信息",
        "concerns": "往年分数线,就业怎么样,招生群",
        "riskPreference": "想冲刺",
        "intentSignals": "提供分数,询问分数线",
        "summary": "广西物理类考生",
        "confidence": "1.4",
    }

    # Act
    result = normalize_llm_extracted_info(raw, raw_text="广西物理类530分")

    # Assert
    assert result.score == 530
    assert result.rank == 32000
    assert result.interestedMajors == ["电子信息"]
    assert result.concerns == ["专业分数线", "就业前景", "招生联系方式"]
    assert result.contactIntent is True
    assert result.riskPreference == "冲刺"
    assert result.confidence == 1.0


def test_hybrid_extractor_falls_back_to_rule_when_llm_request_fails():
    # Arrange
    llm = LLMExtractor(
        config=enabled_llm_config(),
        client=FakeLLMClient(error=LLMExtractionError("boom")),
    )
    extractor = HybridExtractor(llm_extractor=llm, rule_extractor=RuleBasedExtractor())
    extractor.config.enabled = True
    extractor.config.api_key = "test-key"

    # Act
    result = extractor.extract("我是广东物理类考生，585分，想问人工智能稳不稳。")

    # Assert
    assert result.extractor == "rule_fallback"
    assert result.province == "广东"
    assert result.score == 585


def test_process_consultation_turn_accepts_mock_llm_extractor():
    # Arrange
    store = MemoryStore()

    # Act
    result = processConsultationTurn(
        store,
        tenantId="tenant_scnu",
        studentId="stu_mock_001",
        sessionId="session_mock_001",
        userMessage="手动输入",
        aiReply="模拟回复",
        extractor=MockExtractor(),
        now="2026-06-17T00:00:00Z",
    )

    # Assert
    assert result.extractionMethod == "llm"
    assert result.profile.province == "广东"
    assert result.profile.score == 585
    assert "宿舍" in result.profile.concerns
    assert result.report.totalStudents == 1


def test_multi_turn_llm_missing_fields_do_not_clear_existing_profile():
    # Arrange
    store = MemoryStore()

    class FirstExtractor:
        def extract(self, user_message, ai_reply=None):
            return ExtractedStudentInfo(
                province="广东",
                subjectType="物理类",
                score=585,
                rank=None,
                interestedMajors=["人工智能"],
                concerns=["录取概率"],
                contactIntent=None,
                rawText=user_message,
                extractor="llm",
            )

    class SecondExtractor:
        def extract(self, user_message, ai_reply=None):
            return ExtractedStudentInfo(
                province=None,
                subjectType=None,
                score=None,
                rank=None,
                interestedMajors=[],
                concerns=["宿舍"],
                contactIntent=None,
                rawText=user_message,
                extractor="llm",
            )

    # Act
    processConsultationTurn(
        store,
        tenantId="tenant_scnu",
        studentId="stu_llm_001",
        sessionId="session_llm_001",
        userMessage="我是广东物理类585分",
        aiReply="可以关注人工智能",
        extractor=FirstExtractor(),
        now="2026-06-17T00:00:00Z",
    )
    result = processConsultationTurn(
        store,
        tenantId="tenant_scnu",
        studentId="stu_llm_001",
        sessionId="session_llm_001",
        userMessage="宿舍怎么样？",
        aiReply="宿舍条件较好",
        extractor=SecondExtractor(),
        now="2026-06-17T00:01:00Z",
    )

    # Assert
    assert result.profile.province == "广东"
    assert result.profile.subjectType == "物理类"
    assert result.profile.score == 585
    assert "人工智能" in result.profile.interestedMajors
    assert "宿舍" in result.profile.concerns


def test_different_student_ids_do_not_mix_profiles():
    # Arrange
    store = MemoryStore()

    # Act
    first = processConsultationTurn(
        store,
        tenantId="tenant_scnu",
        studentId="stu_a",
        sessionId="session_a",
        userMessage="我是广东物理类考生，585分，想问人工智能。",
        aiReply="可以关注人工智能。",
        now="2026-06-17T00:00:00Z",
    )
    second = processConsultationTurn(
        store,
        tenantId="tenant_scnu",
        studentId="stu_b",
        sessionId="session_b",
        userMessage="我是湖南历史类考生，560分，想问汉语言文学。",
        aiReply="可以关注汉语言文学。",
        now="2026-06-17T00:01:00Z",
    )

    # Assert
    assert first.profile.studentId == "stu_a"
    assert second.profile.studentId == "stu_b"
    assert first.profile.province == "广东"
    assert second.profile.province == "湖南"
    assert "人工智能" in first.profile.interestedMajors
    assert "汉语言文学" in second.profile.interestedMajors
    assert store.get_profile("tenant_scnu", "stu_a").province == "广东"
    assert store.get_profile("tenant_scnu", "stu_b").province == "湖南"


def test_json_data_link_store_reads_and_writes_mock_files():
    # Arrange
    with TemporaryDirectory() as tmp_dir:
        store = JsonDataLinkStore(tmp_dir)

        # Act
        result = processConsultationTurn(
            store,
            tenantId="tenant_scnu",
            studentId="stu_json_001",
            sessionId="session_json_001",
            userMessage="我是广东物理类考生，585分，想问人工智能。",
            aiReply="可以关注人工智能和软件工程。",
            now="2026-06-17T00:00:00Z",
        )
        reloaded = JsonDataLinkStore(tmp_dir)

        # Assert
        assert reloaded.get_session("session_json_001").sessionId == "session_json_001"
        assert reloaded.get_profile("tenant_scnu", "stu_json_001").score == 585
        assert len(reloaded.list_profiles("tenant_scnu")) == 1
        assert len(reloaded.list_sessions("tenant_scnu")) == 1
        assert result.report.totalStudents == 1


if __name__ == "__main__":
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
    print(f"data-link tests passed: {len(tests)}")
