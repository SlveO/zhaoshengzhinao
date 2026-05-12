from enum import Enum
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class Stage(str, Enum):
    OPEN = "open"
    EXPLORE = "explore"
    FOCUS = "focus"
    CONFIRM = "confirm"
    DONE = "done"

STAGE_ORDER = [Stage.OPEN, Stage.EXPLORE, Stage.FOCUS, Stage.CONFIRM, Stage.DONE]

class ConversationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    stage: Stage
    slots: dict
    stage_complete: bool
    summary_pending: bool
