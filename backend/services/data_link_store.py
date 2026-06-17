"""Development-only JSON storage adapter for the data link pipeline.

JsonDataLinkStore writes human-readable mock files for demo and manual testing.
It implements the same store protocol expected by the core pipeline, so A group
can later replace it with a DatabaseDataLinkStore without changing extraction,
profile merge, scoring, or report logic.
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import TypeVar

from services.data_link import (
    ChatMessage,
    ChatSession,
    ConsultationReport,
    DataLinkStore,
    StudentProfile,
    to_plain_dict,
)


T = TypeVar("T")


class JsonDataLinkStore(DataLinkStore):
    """Persist sessions, profiles, and report snapshots as local JSON files."""

    def __init__(self, base_dir: str | Path = "data/mock"):
        self.base_dir = Path(base_dir)
        self.sessions_path = self.base_dir / "chat_sessions.json"
        self.profiles_path = self.base_dir / "student_profiles.json"
        self.report_path = self.base_dir / "report_summary.json"
        self.ensure_files()

    def ensure_files(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.sessions_path, self.profiles_path):
            if not path.exists():
                self._write_json(path, [])
        if not self.report_path.exists():
            self._write_json(self.report_path, {})

    def reset(self) -> None:
        self._write_json(self.sessions_path, [])
        self._write_json(self.profiles_path, [])
        self._write_json(self.report_path, {})

    def get_session(self, session_id: str) -> ChatSession | None:
        for session in self.list_sessions():
            if session.sessionId == session_id:
                return session
        return None

    def upsert_session(self, session: ChatSession) -> None:
        sessions = self.list_sessions()
        updated = False
        for index, existing in enumerate(sessions):
            if existing.sessionId == session.sessionId:
                sessions[index] = session
                updated = True
                break
        if not updated:
            sessions.append(session)
        self._write_json(self.sessions_path, [to_plain_dict(item) for item in sessions])

    def get_profile(self, tenant_id: str, student_id: str) -> StudentProfile | None:
        for profile in self.list_profiles(tenant_id):
            if profile.studentId == student_id:
                return profile
        return None

    def upsert_profile(self, profile: StudentProfile) -> None:
        profiles = self.list_profiles()
        updated = False
        for index, existing in enumerate(profiles):
            if existing.tenantId == profile.tenantId and existing.studentId == profile.studentId:
                profiles[index] = profile
                updated = True
                break
        if not updated:
            profiles.append(profile)
        self._write_json(self.profiles_path, [to_plain_dict(item) for item in profiles])

    def list_profiles(self, tenant_id: str | None = None) -> list[StudentProfile]:
        profiles = [_from_dict(StudentProfile, item) for item in self._read_json(self.profiles_path, [])]
        if tenant_id:
            return [item for item in profiles if item.tenantId == tenant_id]
        return profiles

    def list_sessions(self, tenant_id: str | None = None) -> list[ChatSession]:
        sessions = [_session_from_dict(item) for item in self._read_json(self.sessions_path, [])]
        if tenant_id:
            return [item for item in sessions if item.tenantId == tenant_id]
        return sessions

    def save_report(self, report: ConsultationReport) -> None:
        self._write_json(self.report_path, to_plain_dict(report))

    def _read_json(self, path: Path, default):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return default

    def _write_json(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")


def _from_dict(cls: type[T], data: dict) -> T:
    allowed = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in allowed})


def _session_from_dict(data: dict) -> ChatSession:
    session_data = dict(data)
    session_data["messages"] = [_from_dict(ChatMessage, item) for item in session_data.get("messages", [])]
    return _from_dict(ChatSession, session_data)
