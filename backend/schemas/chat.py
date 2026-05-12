from pydantic import BaseModel

class ChatMessage(BaseModel):
    type: str          # "message" | "thinking" | "stage_change" | "profile_update" | "summary"
    role: str | None = None
    content: str | None = None
    stage: str | None = None
    field: str | None = None
    value: dict | None = None
    confidence: float | None = None
    profile_snapshot: dict | None = None

class WSMessage(BaseModel):
    type: str
    content: str
    session_id: str
