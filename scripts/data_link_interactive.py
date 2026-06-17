"""Interactive local tester for the data link pipeline."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from services.data_link import processConsultationTurn  # noqa: E402
from services.data_link_llm import load_llm_config  # noqa: E402
from services.data_link_store import JsonDataLinkStore  # noqa: E402


DEFAULT_TENANT_ID = "tenant_scnu"
DEFAULT_STUDENT_ID = "stu_manual_001"
DEFAULT_SESSION_ID = "session_manual_001"
EXIT_WORDS = {"exit", "quit"}


def prompt_with_default(label: str, default: str) -> str:
    value = read_terminal_input(f"{label} [{default}]: ").strip()
    return value or default


def read_terminal_input(prompt: str) -> str:
    try:
        return clean_terminal_text(input(prompt))
    except EOFError:
        return ""


def clean_terminal_text(value: str) -> str:
    """Drop invalid surrogate characters that can appear in Windows piped input."""
    return value.encode("utf-8", "replace").decode("utf-8")


def should_exit(value: str) -> bool:
    return value.strip().lower() in EXIT_WORDS


def print_json(title: str, value) -> None:
    print(f"\n{title}")
    print(json.dumps(asdict(value), ensure_ascii=False, indent=2))


def print_round_result(result) -> None:
    print("\n本轮提取方式 extractor:", result.extractionMethod)
    print_json("本轮提取出的 extractedInfo:", result.extractedInfo)
    print_json("当前学生画像 profile:", result.profile)
    print("\n当前意向分 intentScore:", result.profile.intentScore)
    print("当前意向等级 intentLevel:", result.profile.intentLevel)
    print("当前标签 tags:", ", ".join(result.profile.tags) if result.profile.tags else "无")
    report = result.report
    summary = {
        "totalStudents": report.totalStudents,
        "highIntentCount": report.highIntentCount,
        "mediumIntentCount": report.mediumIntentCount,
        "lowIntentCount": report.lowIntentCount,
        "hotMajors": report.hotMajors[:5],
        "hotConcerns": report.hotConcerns[:5],
    }
    print("\n报告摘要 reportSummary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n继续输入下一轮学生咨询；输入 exit / quit 或直接回车结束。")


def main() -> None:
    print("数据链路交互式本地测试")
    print("本脚本使用 data/manual_test/，不会覆盖 data/mock/ demo 文件。")
    print("输入 exit / quit 或在学生输入处直接回车可结束。\n")
    config = load_llm_config()
    print("当前提取模式：hybrid")
    print(f"LLM enabled: {str(config.enabled).lower()}")
    print(f"LLM key found: {str(config.key_found).lower()}")
    if not config.key_found:
        print("未检测到 DATA_LINK_LLM_API_KEY，将自动使用规则提取。\n")

    tenant_id = prompt_with_default("tenantId", DEFAULT_TENANT_ID)
    student_id = prompt_with_default("studentId", DEFAULT_STUDENT_ID)
    session_id = prompt_with_default("sessionId", DEFAULT_SESSION_ID)
    store = JsonDataLinkStore(ROOT / "data" / "manual_test")

    round_index = 1
    while True:
        print(f"\n第 {round_index} 轮")
        user_message = read_terminal_input("学生输入 userMessage: ").strip()
        if not user_message or should_exit(user_message):
            print("已结束交互式测试。")
            break

        ai_reply = read_terminal_input("AI 回复 aiReply: ").strip()
        if not ai_reply or should_exit(ai_reply):
            print("已结束交互式测试。")
            break

        result = processConsultationTurn(
            store,
            tenantId=tenant_id,
            studentId=student_id,
            sessionId=session_id,
            userMessage=user_message,
            aiReply=ai_reply,
        )
        print_round_result(result)
        round_index += 1


if __name__ == "__main__":
    main()
