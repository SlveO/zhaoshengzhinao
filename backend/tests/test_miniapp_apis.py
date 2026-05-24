"""
C端 5 API 完整测试套件
运行方式: cd backend && python tests/test_miniapp_apis.py
分两层: Layer 1 (无DB) — 模块导入/路由/Schema/纯函数逻辑
        Layer 2 (需DB) — 需要 PostgreSQL + Docker 运行
"""
import sys
import json
import asyncio


# ═══════════════════════════════════════════
# Layer 1: 无数据库依赖测试
# ═══════════════════════════════════════════

def test_import_models():
    """验证 Model 层可正常导入"""
    from models.consult_session import ConsultSession
    from models.chat_message import ChatMessage
    assert ConsultSession.__tablename__ == "consult_sessions"
    assert ChatMessage.__tablename__ == "chat_messages"
    assert hasattr(ConsultSession, "session_id")
    assert hasattr(ConsultSession, "province")
    assert hasattr(ConsultSession, "score")
    assert hasattr(ChatMessage, "role")
    assert hasattr(ChatMessage, "content")
    print("  PASS test_import_models")


def test_recommendation_model_extended():
    """验证 Recommendation 模型新增 session_id 列"""
    from models.recommendation import Recommendation
    assert hasattr(Recommendation, "session_id"), "缺少 session_id 列"
    # user_id 应为 nullable
    col = Recommendation.__table__.columns["user_id"]
    assert col.nullable is True, "user_id 应为 nullable"
    print("  PASS test_recommendation_model_extended")


def test_import_schemas():
    """验证 Schema 层可正常导入"""
    from schemas.miniapp import (
        EnterRequest, ChatMessageRequest, RecommendationRequest,
        EnterData, ChatMessageData, StudentProfileData,
        RecommendationData, MajorAnalysisData,
    )
    # 测试请求模型默认值
    req = EnterRequest()
    assert req.session_id is None
    assert req.tenant_slug == "scnu"
    assert req.scene == "miniapp_enter"
    print("  PASS test_import_schemas")


def test_schema_validation():
    """验证 Pydantic Schema 的序列化和默认值"""
    from schemas.miniapp import (
        EnterRequest, EnterData, StudentProfileData,
        ChatMessageRequest, MessageBody,
    )

    # EnterRequest: 首次进入
    r = EnterRequest(session_id=None, tenant_slug="scnu")
    d = r.model_dump()
    assert d["session_id"] is None
    assert d["tenant_slug"] == "scnu"

    # EnterRequest: 再次进入
    r = EnterRequest(session_id="sess_abc123", tenant_slug="scnu")
    d = r.model_dump()
    assert d["session_id"] == "sess_abc123"

    # ChatMessageRequest
    r = ChatMessageRequest(
        session_id="sess_abc123",
        tenant_slug="scnu",
        message=MessageBody(role="user", content="广东585分能报华师吗？"),
    )
    d = r.model_dump()
    assert d["message"]["role"] == "user"
    assert "585" in d["message"]["content"]

    # EnterData: 新会话
    data = EnterData(
        session_id="sess_new001",
        tenant_slug="scnu",
        tenant_name="华南师范大学",
        is_new_session=True,
        has_profile=False,
        chat_history=[],
        profile_summary=None,
    )
    assert data.model_dump()["is_new_session"] is True

    # EnterData: 恢复会话
    data = EnterData(
        session_id="sess_exist001",
        tenant_slug="scnu",
        tenant_name="华南师范大学",
        is_new_session=False,
        has_profile=True,
        chat_history=[
            {"message_id": "m1", "role": "assistant", "content": "你好", "created_at": "2026-05-24T10:00:00+08:00"},
        ],
        profile_summary={"province": "广东", "subject_type": "物理类", "score": 585},
    )
    j = data.model_dump()
    assert len(j["chat_history"]) == 1
    assert j["profile_summary"]["province"] == "广东"

    # StudentProfileData: 无档案
    data = StudentProfileData(session_id="sess_x", has_profile=False, profile=None)
    assert data.model_dump()["has_profile"] is False
    assert data.model_dump()["profile"] is None

    print("  PASS test_schema_validation")


def test_import_services():
    """验证 Service 层可正常导入"""
    from services.consult_service import (
        get_or_create_session, get_session, get_chat_history,
        save_message, update_session_profile,
        extract_profile_from_message, build_profile_summary,
    )
    # 验证所有函数都是 async (callable + coroutine)
    import inspect
    for name in ["get_or_create_session", "get_session", "get_chat_history",
                 "save_message", "update_session_profile", "extract_profile_from_message"]:
        fn = locals()[name]
        assert inspect.iscoroutinefunction(fn), f"{name} 应为 async function"
    print("  PASS test_import_services")


def test_extract_profile_from_message_logic():
    """验证档案抽取的纯逻辑（不需要 DB）"""
    from services.consult_service import extract_profile_from_message

    async def run():
        # 测试1: 抽取省份+科类+分数
        updates = await extract_profile_from_message(
            "广东物理类 585 分能报华师吗",
            "根据广东物理类585分的成绩...",
            {},  # 空档案
        )
        assert updates.get("province") == "广东", f"应为广东, 实际: {updates.get('province')}"
        assert updates.get("subject_type") == "物理类", f"应为物理类, 实际: {updates.get('subject_type')}"
        assert updates.get("score") == 585, f"应为585, 实际: {updates.get('score')}"

        # 测试2: 已有档案不覆盖
        updates = await extract_profile_from_message(
            "北京理科生 620 分",
            "你是北京来的理科生",
            {"province": "广东", "subject_type": "物理类", "score": 585},
        )
        assert "province" not in updates, "已有省份不应覆盖"
        assert "subject_type" not in updates, "已有科类不应覆盖"
        assert "score" not in updates, "已有分数不应覆盖"

        # 测试3: 空消息
        updates = await extract_profile_from_message("你好", "你好，有什么可以帮你", {})
        assert len(updates) == 0, f"空消息不应产生更新: {updates}"

        # 测试4: 历史类
        updates = await extract_profile_from_message(
            "我是历史类考生", "历史类可以报考师范专业", {}
        )
        assert updates.get("subject_type") == "历史类"

        print("  PASS test_extract_profile_from_message_logic (4 cases)")

    asyncio.get_event_loop().run_until_complete(run())


def test_build_profile_summary():
    """验证档案摘要构建逻辑"""
    from models.consult_session import ConsultSession

    # 空 session: 应返回 None
    s = ConsultSession(session_id="test001", tenant_slug="scnu")
    from services.consult_service import build_profile_summary
    result = build_profile_summary(s)
    assert result is None, f"空档案应返回 None, 实际: {result}"

    # 有部分数据的 session
    s.province = "广东"
    s.score = 600
    result = build_profile_summary(s)
    assert result is not None
    assert result["province"] == "广东"
    assert result["score"] == 600
    assert result["subject_type"] is None  # 空字符串转 None
    assert result["intent_majors"] == []

    print("  PASS test_build_profile_summary")


def test_import_routes():
    """验证路由模块导入，5 个端点正确注册"""
    from api.routes.miniapp import router

    routes = router.routes
    assert len(routes) == 5, f"应为 5 个路由, 实际: {len(routes)}"

    # 验证 HTTP 方法和路径
    route_map = {}
    for r in routes:
        methods = r.methods
        path = r.path
        if "POST" in methods:
            route_map[("POST", path)] = True
        if "GET" in methods:
            route_map[("GET", path)] = True

    expected = [
        ("POST", "/api/v1/miniapp/enter"),
        ("POST", "/api/v1/chat/messages"),
        ("GET", "/api/v1/student/profile"),
        ("POST", "/api/v1/recommendations"),
        ("GET", "/api/v1/majors/analysis"),
    ]
    for method, path in expected:
        assert (method, path) in route_map, f"缺少路由: {method} {path}"

    print("  PASS test_import_routes (5 endpoints verified)")


def test_ok_err_helpers():
    """验证统一响应格式辅助函数"""
    from api.routes.miniapp import ok, err

    # ok() — 成功响应
    resp = ok({"session_id": "abc"})
    assert resp["data"] == {"session_id": "abc"}
    assert resp["error"] is None

    # err() — 错误响应
    resp = err("SESSION_NOT_FOUND", "会话不存在")
    assert resp["data"] is None
    assert resp["error"]["code"] == "SESSION_NOT_FOUND"
    assert resp["error"]["message"] == "会话不存在"

    print("  PASS test_ok_err_helpers")


def test_route_conflicts():
    """验证 miniapp 路由与现有路由无冲突"""
    from api.routes.miniapp import router as miniapp_router
    from api.routes.recommendation import router as rec_router
    from api.routes.chat import router as chat_router

    # 辅助: 提取路由的方法+路径 (兼容 WebSocket 路由)
    def get_route_methods(route):
        if hasattr(route, "methods"):
            return route.methods
        return set()

    # 现有 recommendation 路由 (无 prefix, 在 main.py 加 /api/v1/recommendations)
    rec_flat = set()
    for r in rec_router.routes:
        for m in get_route_methods(r):
            rec_flat.add((m, "/api/v1/recommendations" + r.path))

    # miniapp 的 POST /api/v1/recommendations vs rec 的 GET /api/v1/recommendations
    # 方法不同 → 不冲突
    miniapp_rec_path = ("POST", "/api/v1/recommendations")
    assert miniapp_rec_path not in rec_flat, \
        f"路由冲突: miniapp POST /recommendations 与现有路由重叠"

    # 现有 chat 路由 (prefix /api/v1/chat, 含 WebSocket 路由)
    chat_flat = set()
    for r in chat_router.routes:
        for m in get_route_methods(r):
            chat_flat.add((m, "/api/v1/chat" + r.path))

    miniapp_chat_path = ("POST", "/api/v1/chat/messages")
    assert miniapp_chat_path not in chat_flat, \
        f"路由冲突: miniapp POST /chat/messages 与现有 WebSocket 路由重叠"

    print("  PASS test_route_conflicts")


def test_migration_structure():
    """验证 migration 文件结构正确"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "migration_005",
        "migrations/versions/005_counsel_tables.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "005"
    assert mod.down_revision == "004"
    assert callable(mod.upgrade)
    assert callable(mod.downgrade)
    print("  PASS test_migration_structure")


# ═══════════════════════════════════════════
# Layer 2: 需要数据库的测试 (标记为 DB_REQUIRED)
# ═══════════════════════════════════════════

async def test_session_create_read_cycle():
    """DB: 创建会话 → 读取会话 → 更新档案 → 保存消息 → 读取历史"""
    from services.consult_service import (
        get_or_create_session, get_session, update_session_profile,
        save_message, get_chat_history, build_profile_summary,
    )

    # 1. 创建新会话
    session, is_new = await get_or_create_session(None, "scnu")
    assert is_new is True
    assert session.session_id.startswith("sess_")
    sid = session.session_id

    # 2. 通过 session_id 读取
    s2 = await get_session(sid)
    assert s2 is not None
    assert s2.tenant_slug == "scnu"

    # 3. 更新档案
    await update_session_profile(sid, {
        "province": "广东",
        "subject_type": "物理类",
        "score": 600,
        "consult_stage": "profile_ready",
    })
    s3 = await get_session(sid)
    assert s3.province == "广东"
    assert s3.score == 600
    assert s3.consult_stage == "profile_ready"

    # 4. 保存消息
    m1 = await save_message(sid, "user", "广东600分能报什么专业")
    assert m1["role"] == "user"
    await save_message(sid, "assistant", "你可以考虑计算机、软件工程...")

    # 5. 读取历史
    history = await get_chat_history(sid)
    assert len(history) >= 2
    assert history[0]["role"] in ("user", "assistant")

    # 6. 档案摘要
    summary = build_profile_summary(s3)
    assert summary["province"] == "广东"
    assert summary["score"] == 600

    print(f"  PASS test_session_create_read_cycle (session_id={sid})")


async def test_session_restore():
    """DB: 恢复已有会话"""
    from services.consult_service import get_or_create_session

    # 用已知 session_id 恢复
    session, is_new = await get_or_create_session("sess_test_restore_001", "scnu")
    if is_new:
        # 首次创建
        session, is_new = await get_or_create_session("sess_test_restore_001", "scnu")
        assert is_new is False  # 第二次应该是恢复
    # else: 之前已存在

    print(f"  PASS test_session_restore (is_new={is_new})")


async def test_message_persistence():
    """DB: 验证消息按时间排序"""
    from services.consult_service import save_message, get_chat_history

    sid = "sess_test_msg_sort"
    await save_message(sid, "user", "msg1")
    await asyncio.sleep(0.1)
    await save_message(sid, "assistant", "msg2")
    await asyncio.sleep(0.1)
    await save_message(sid, "user", "msg3")

    history = await get_chat_history(sid)
    assert len(history) >= 3
    # 验证升序
    roles = [m["role"] for m in history[-3:]]
    assert roles == ["user", "assistant", "user"], f"消息顺序错误: {roles}"

    print(f"  PASS test_message_persistence (3 messages)")


# ═══════════════════════════════════════════
# 运行器
# ═══════════════════════════════════════════

def run_layer1():
    """Layer 1: 无 DB 测试"""
    print("\n" + "=" * 55)
    print("Layer 1: 无数据库依赖测试 (共 10 项)")
    print("=" * 55)

    tests = [
        test_import_models,
        test_recommendation_model_extended,
        test_import_schemas,
        test_schema_validation,
        test_import_services,
        test_extract_profile_from_message_logic,
        test_build_profile_summary,
        test_import_routes,
        test_ok_err_helpers,
        test_route_conflicts,
        test_migration_structure,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1

    print(f"\n  Layer 1 Result: {passed}/{passed+failed} passed")
    return passed, failed


def run_layer2():
    """Layer 2: 需 DB 测试"""
    print("\n" + "=" * 55)
    print("Layer 2: 数据库依赖测试 (共 3 项)")
    print("=" * 55)

    tests = [
        test_session_create_read_cycle,
        test_session_restore,
        test_message_persistence,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            asyncio.get_event_loop().run_until_complete(t())
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n  Layer 2 Result: {passed}/{passed+failed} passed")
    return passed, failed


if __name__ == "__main__":
    print("C端 5 API 测试套件")
    print(f"Python: {sys.version}")

    l1_pass, l1_fail = run_layer1()

    # Layer 2 只在有数据库时运行
    try:
        from models import async_session
        l2_pass, l2_fail = run_layer2()
    except Exception as e:
        print(f"\n  Layer 2 SKIPPED — 数据库不可用 ({e})")
        l2_pass, l2_fail = 0, 0

    total_pass = l1_pass + l2_pass
    total_fail = l1_fail + l2_fail

    print("\n" + "=" * 55)
    print(f"Total: {total_pass} passed, {total_fail} failed")
    if total_fail > 0:
        print("RESULT: FAIL")
        sys.exit(1)
    else:
        print("RESULT: PASS")
