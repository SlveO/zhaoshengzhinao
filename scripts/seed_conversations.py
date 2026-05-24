"""Seed 50 simulated student conversations for demo analytics.

Generates realistic event_logs and session_profiles so the admin
dashboard shows non-zero data for funnel, profile dashboard, etc.
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from random import choice, randint, random

_backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)

from sqlalchemy import text
from models import async_session

# ── Config ──

TENANT_SLUG = "scnu"
NUM_SESSIONS = 50

STAGES = ["open", "open", "open", "explore", "explore", "explore", "focus", "focus", "confirm", "done"]
RIASEC_DIMS = ["riasec_R", "riasec_I", "riasec_A", "riasec_S", "riasec_E", "riasec_C"]
VALUES = ["社会贡献", "个人成长", "工作稳定", "薪资水平"]
PROVINCES = ["广东", "广东", "广东", "广东", "湖南", "广西", "江西", "福建", "湖北", "四川"]

TOPICS = [
    "我对计算机编程比较感兴趣，有什么专业推荐？",
    "我数学成绩不错，哪些专业适合我？",
    "想了解一下学校的就业情况怎么样？",
    "我比较喜欢和人打交道，有什么建议？",
    "你们学校有什么特色专业？",
    "师范类专业毕业后好就业吗？",
    "我想了解一下宿舍和校园环境",
    "分数刚好过线有什么专业可以选？",
    "我对心理学很感兴趣",
    "物理和化学哪个方向更适合我？",
    "爸妈想让我学医但我更喜欢文科",
    "你们学校转专业方便吗？",
    "计算机和软件工程有什么区别？",
    "光学工程这个专业以后能做什么？",
    "我喜欢画画，有没有设计类的专业？",
]


async def seed():
    async with async_session() as db:
        # Get SCNU tenant ID
        result = await db.execute(text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": TENANT_SLUG})
        tid = result.scalar_one()
        print(f"Tenant: {TENANT_SLUG} ({tid})")

        now = datetime.now(timezone.utc)
        visitor_count = 0
        conversation_count = 0
        deep_count = 0
        intent_count = 0

        for i in range(NUM_SESSIONS):
            uid = uuid.uuid4()
            sid = uuid.uuid4()
            start_time = now - timedelta(days=randint(0, 14), hours=randint(0, 23))

            # 1. page.viewed event (visitor entry)
            await db.execute(text("""
                INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                VALUES (:id, :tid, 'page.viewed', :uid, :sid, :payload, :ts)
            """), {
                "id": uuid.uuid4(), "tid": tid, "uid": uid, "sid": sid,
                "payload": json.dumps({"page": "/chat", "source": "scan"}),
                "ts": start_time,
            })
            visitor_count += 1

            # 2. Simulate conversation (3-12 turns)
            turns = randint(3, 12)
            current_stage = "open"
            dims_covered = set()
            vals_covered = []

            for t in range(turns):
                event_time = start_time + timedelta(seconds=t * randint(30, 120))

                # chat.message_sent
                topic = choice(TOPICS) if t == 0 else ""
                emotion = choice([None, "兴奋", "迷茫", None, None])
                await db.execute(text("""
                    INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                    VALUES (:id, :tid, 'chat.message_sent', :uid, :sid, :payload, :ts)
                """), {
                    "id": uuid.uuid4(), "tid": tid, "uid": uid, "sid": sid,
                    "payload": json.dumps({"stage": current_stage, "turn": t + 1, "message_length": len(topic) if topic else randint(10, 80), "emotion": emotion}),
                    "ts": event_time,
                })
                conversation_count += 1

                # Stage progression
                if t >= 3 and current_stage == "open":
                    current_stage = "explore"
                    await db.execute(text("""
                        INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                        VALUES (:id, :tid, 'chat.stage_changed', :uid, :sid, :payload, :ts)
                    """), {
                        "id": uuid.uuid4(), "tid": tid, "uid": uid, "sid": sid,
                        "payload": json.dumps({"from_stage": "open", "to_stage": "explore", "turn": t + 1}),
                        "ts": event_time,
                    })
                elif t >= 6 and current_stage == "explore":
                    current_stage = "focus"
                    await db.execute(text("""
                        INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                        VALUES (:id, :tid, 'chat.stage_changed', :uid, :sid, :payload, :ts)
                    """), {
                        "id": uuid.uuid4(), "tid": tid, "uid": uid, "sid": sid,
                        "payload": json.dumps({"from_stage": "explore", "to_stage": "focus", "turn": t + 1}),
                        "ts": event_time,
                    })

                # Accumulate profile dimensions
                if t >= 1 and random() > 0.3:
                    dim = choice(RIASEC_DIMS)
                    dims_covered.add(dim)
                    completeness = "L1"
                    if len(dims_covered) >= 2:
                        completeness = "L2"
                    if len(dims_covered) >= 4 and vals_covered:
                        completeness = "L3"
                    await db.execute(text("""
                        INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                        VALUES (:id, :tid, 'profile.updated', :uid, :sid, :payload, :ts)
                    """), {
                        "id": uuid.uuid4(), "tid": tid, "uid": uid, "sid": sid,
                        "payload": json.dumps({
                            "completeness": completeness,
                            "riasec_dims": list(dims_covered),
                            "confidence": round(0.5 + len(dims_covered) * 0.08, 2),
                        }),
                        "ts": event_time,
                    })
                    if completeness in ("L2", "L3"):
                        deep_count += 1

                if t >= 4 and random() > 0.5 and not vals_covered:
                    vals_covered = [choice(VALUES)]
                    await db.execute(text("""
                        INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                        VALUES (:id, :tid, 'profile.updated', :uid, :sid, :payload, :ts)
                    """), {
                        "id": uuid.uuid4(), "tid": tid, "uid": uid, "sid": sid,
                        "payload": json.dumps({
                            "completeness": "L3" if len(dims_covered) >= 4 else "L2",
                            "riasec_dims": list(dims_covered),
                            "values": vals_covered,
                            "confidence": 0.75,
                        }),
                        "ts": event_time,
                    })
                    deep_count += 1

            # 3. recommendation.generated (60% of sessions)
            if random() > 0.4:
                await db.execute(text("""
                    INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                    VALUES (:id, :tid, 'recommendation.generated', :uid, :sid, :payload, :ts)
                """), {
                    "id": uuid.uuid4(), "tid": tid, "uid": uid, "sid": sid,
                    "payload": json.dumps({"profile_level": completeness, "candidates_count": 30, "output_count": 10}),
                    "ts": start_time + timedelta(seconds=turns * 60),
                })

            # 4. page.intent_expressed (40% of sessions)
            if random() > 0.6:
                await db.execute(text("""
                    INSERT INTO event_logs (id, tenant_id, event_type, user_id, session_id, payload, created_at)
                    VALUES (:id, :tid, 'page.intent_expressed', :uid, :sid, :payload, :ts)
                """), {
                    "id": uuid.uuid4(), "tid": tid, "uid": uid, "sid": sid,
                    "payload": json.dumps({"colleges_of_interest": ["华南师范大学"], "majors_of_interest": ["计算机科学与技术", "心理学"]}),
                    "ts": start_time + timedelta(seconds=turns * 90),
                })
                intent_count += 1

            # 5. session_profiles snapshot (user_id=NULL for anonymous guests)
            riasec = {}
            for dim in dims_covered:
                riasec[dim.replace("riasec_", "")] = randint(4, 9)
            await db.execute(text("""
                INSERT INTO session_profiles (id, tenant_id, session_id, user_id, profile_json, confidence_json, completeness, created_at)
                VALUES (:id, :tid, :sid, NULL, :profile, :conf, :comp, :ts)
            """), {
                "id": uuid.uuid4(), "tid": tid, "sid": sid,
                "profile": json.dumps({
                    "riasec": riasec,
                    "values": vals_covered,
                    "region_pref": [choice(PROVINCES)],
                    "score": randint(520, 650),
                    "subjects": choice(["物理", "历史", "物理+化学"]),
                }),
                "conf": json.dumps({"avg": round(0.5 + len(dims_covered) * 0.08, 2)}),
                "comp": completeness,
                "ts": start_time + timedelta(seconds=turns * 90),
            })

            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{NUM_SESSIONS} sessions seeded...")

        await db.commit()
        print(f"\nDone. Seeded {NUM_SESSIONS} sessions:")
        print(f"  visitors:        {visitor_count}")
        print(f"  conversations:   {conversation_count}")
        print(f"  deepConsultations: {deep_count}")
        print(f"  intentExpressed: {intent_count}")
        print(f"  Conversion: visitor→conversation = {conversation_count}/{visitor_count}")
        print(f"  Conversion: conversation→deep = {deep_count}/{conversation_count}")
        print(f"  Conversion: deep→intent = {intent_count}/{deep_count}")


if __name__ == "__main__":
    asyncio.run(seed())
