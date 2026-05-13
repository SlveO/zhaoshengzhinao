# -*- coding: utf-8 -*-
"""E2E Smoke Test: register -> chat -> recommendations. Run with: python scripts/smoke_test.py"""
import asyncio, json, sys, time, urllib.request

API = "http://127.0.0.1:8000"

CHAT_SCRIPT = [
    "我喜欢做化学实验，特别是合成新物质的过程",
    "我平时还喜欢看科普视频，关于生物进化和基因编辑的",
    "理科里面我最擅长化学和生物，物理一般",
    "我希望以后能做有意义的工作，能帮助到别人",
    "我想留在广东读大学，广州深圳都可以",
    "社会贡献第一，个人成长第二",
    "是的，我对这些信息没有异议",
]


def api(method, path, body=None, token=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


async def run():
    print("=" * 50)
    print("  Gaokao Advisor - Smoke Test")
    print("=" * 50)

    # Step 1: Register
    print("\n[1/4] Registering new user...")
    username = f"smoke_{int(time.time())}"
    r = api("POST", "/api/v1/auth/register", {
        "username": username,
        "password": "test123456",
        "region": "广东",
        "score": 610,
        "subjects": "物理+化学+生物",
    })
    token = r["access_token"]
    print(f"  User: {username}")

    # Step 2: Create session
    print("\n[2/4] Creating chat session...")
    r = api("POST", "/api/v1/chat/session", token=token)
    sid = r["session_id"]
    print(f"  Session: {sid}")

    # Step 3: WebSocket conversation
    print(f"\n[3/4] Simulating {len(CHAT_SCRIPT)} rounds of conversation...")
    import websockets

    async with websockets.connect(f"ws://127.0.0.1:8000/api/v1/chat/session/{sid}") as ws:
        await ws.recv()
        await ws.recv()  # skip initial profile_update + stage_change

        for i, msg in enumerate(CHAT_SCRIPT):
            t0 = time.time()
            await ws.send(json.dumps({"type": "message", "content": msg, "session_id": sid}))

            stage = "?"
            slots = {}
            while True:
                m = json.loads(await ws.recv())
                if m["type"] == "message" and m["role"] == "assistant":
                    reply = m["content"][:40]
                    stage = m.get("stage", "?")
                if m["type"] == "profile_update":
                    slots = m.get("value", {})
                if m["type"] == "summary":
                    print(f"    [SUMMARY] stage={m.get('stage')}")
                if m["type"] in ("stage_change",):
                    break

            t1 = time.time()
            riasec = slots.get("riasec", {})
            top_riasec = dict(sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:3]) if riasec else {}
            values = slots.get("values", [])
            region = slots.get("region_pref", [])
            print(f"  [{i + 1}/7] {t1 - t0:.1f}s | stage={stage} | riasec={top_riasec} | values={values} | region={region}")

    # Step 4: Recommendations
    print("\n[4/4] Fetching recommendations...")
    t0 = time.time()
    r = api("GET", "/api/v1/recommendations", token=token)
    t1 = time.time()
    recs = r.get("recommendations", [])
    profile = r.get("profile_snapshot", {})

    riasec = profile.get("riasec", {})
    top_riasec = dict(sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:3]) if riasec else {}
    print(f"  Profile: score={profile.get('score')} riasec={top_riasec} values={profile.get('values', [])}")
    print(f"  Results: {len(recs)} recommendations in {t1 - t0:.1f}s")
    for rec in recs[:5]:
        reasons = rec.get("reasons", [])
        src = reasons[0]["source"][:30] if reasons else "?"
        print(f"  #{rec['rank']} {rec['college_name']} | {rec['major_name']} | [{rec['category']}] {rec['match_score']}% | src: {src}")

    # Result
    print(f"\n{'=' * 50}")
    ok = len(recs) > 0
    print(f"  Result: {'PASS' if ok else 'FAIL'}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(run())
