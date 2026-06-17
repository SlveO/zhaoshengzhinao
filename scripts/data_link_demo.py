"""Run the local JSON data link demo."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from services.data_link import processConsultationTurn  # noqa: E402
from services.data_link_store import JsonDataLinkStore  # noqa: E402


DEMO_TURNS = [
    {
        "tenantId": "tenant_scnu",
        "studentId": "stu_demo_001",
        "sessionId": "session_demo_001",
        "userMessage": "我是广东物理类考生，585分，想问人工智能专业稳不稳？",
        "aiReply": "你的分数有一定竞争力，可以重点关注人工智能、软件工程等专业，同时建议参考近三年专业分数线。",
    },
    {
        "tenantId": "tenant_scnu",
        "studentId": "stu_demo_001",
        "sessionId": "session_demo_001",
        "userMessage": "那软件工程和计算机哪个录取概率更高？有招生群吗？",
        "aiReply": "可以继续关注软件工程和计算机科学与技术，招生群信息建议以学校官方招生办发布为准。",
    },
    {
        "tenantId": "tenant_scnu",
        "studentId": "stu_demo_002",
        "sessionId": "session_demo_002",
        "userMessage": "我是湖南历史类，560分，想了解汉语言文学，宿舍条件怎么样？",
        "aiReply": "汉语言文学适合对中文、教育和文化方向感兴趣的考生，宿舍安排以学校当年通知为准。",
    },
    {
        "tenantId": "tenant_scnu",
        "studentId": "stu_demo_002",
        "sessionId": "session_demo_002",
        "userMessage": "入学后可以转专业吗？",
        "aiReply": "转专业通常需要满足学校相关条件，建议关注教务部门发布的最新政策。",
    },
    {
        "tenantId": "tenant_scnu",
        "studentId": "stu_demo_003",
        "sessionId": "session_demo_003",
        "userMessage": "广西物理类530分，电子信息工程就业前景怎么样，往年分数线高吗？",
        "aiReply": "电子信息工程偏工程技术方向，就业面较广，建议结合往年分数线和位次综合判断。",
    },
]


def main() -> None:
    store = JsonDataLinkStore(ROOT / "data" / "mock")
    store.reset()
    result = None
    for turn in DEMO_TURNS:
        result = processConsultationTurn(store, **turn)

    report = result.report if result else None
    hot_major = report.hotMajors[0]["name"] if report and report.hotMajors else "无"
    hot_concern = report.hotConcerns[0]["name"] if report and report.hotConcerns else "无"
    high_count = report.highIntentCount if report else 0

    print("数据链路 demo 运行完成")
    print("已生成 chat_sessions.json")
    print("已生成 student_profiles.json")
    print("已生成 report_summary.json")
    print(f"高意向学生数量：{high_count}")
    print(f"热门专业：{hot_major}")
    print(f"热门关注点：{hot_concern}")


if __name__ == "__main__":
    main()
