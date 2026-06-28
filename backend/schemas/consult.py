"""咨询模块 Pydantic 模型。"""
from pydantic import BaseModel
from typing import Optional


class ConsultMessageRequest(BaseModel):
    """咨询 SSE 消息请求。"""
    session_id: str
    tenant_slug: str = "scnu"
    message: str


class ConsultIntentData(BaseModel):
    """意图提取结果（SSE intent 事件 payload）。"""
    intent_type: str  # "data_query" | "policy_query" | "major_intro" | "chitchat"
    majors: list[str] = []
    province: Optional[str] = None
    year: Optional[int] = None
    need_admission_data: bool = False


class ConsultValidationData(BaseModel):
    """后置校验结果（SSE validation 事件 payload）。"""
    passed: bool
    issues_count: int = 0
    issues: list[dict] = []
    regenerated: bool = False
