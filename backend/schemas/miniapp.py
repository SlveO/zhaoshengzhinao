from pydantic import BaseModel
from typing import Optional


# ── 请求模型 ──

class EnterRequest(BaseModel):
    session_id: Optional[str] = None
    tenant_slug: str = "scnu"
    scene: str = "miniapp_enter"

class MessageBody(BaseModel):
    role: str
    content: str

class ChatMessageRequest(BaseModel):
    session_id: str
    tenant_slug: str = "scnu"
    message: MessageBody

class RecommendationRequest(BaseModel):
    session_id: str
    tenant_slug: str = "scnu"
    profile_snapshot: Optional[dict] = None

# ── 响应模型 ──

class EnterData(BaseModel):
    session_id: str
    tenant_slug: str
    tenant_name: str
    is_new_session: bool
    has_profile: bool
    chat_history: list[dict] = []
    profile_summary: Optional[dict] = None

class ChatMessageData(BaseModel):
    session_id: str
    assistant_message: dict
    profile_updated: bool
    profile_summary: Optional[dict] = None
    sources: list[dict] = []

class StudentProfileData(BaseModel):
    session_id: str
    has_profile: bool
    profile: Optional[dict] = None

class RecommendationData(BaseModel):
    session_id: str
    tenant_slug: str
    tenant_name: str
    items: list[dict]
    disclaimer: str

class MajorAnalysisData(BaseModel):
    session_id: str
    tenant_slug: str
    tenant_name: str
    major: dict
    analysis: dict
