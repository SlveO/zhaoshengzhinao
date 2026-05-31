# Conversation Agent (LangGraph)

Single-node LangGraph state machine at `backend/agents/conversation/`. Stages (OPEN → EXPLORE → FOCUS → CONFIRM → DONE) are managed within the LLM prompt, not as separate graph nodes. One LLM call per turn via DeepSeek API (`deepseek-v4-flash`). State includes messages, slot-filling evidence, and emotion detection from keyword matching. Stored in Redis with 30-min TTL. The graph compiles with a `MemorySaver` checkpointer.

Key files:
- `backend/agents/conversation/agent.py` — graph definition + LLM node
- `backend/agents/conversation/state.py` — ConversationState TypedDict
- `backend/agents/conversation/slot_filler.py` — evidence slot management
- `backend/agents/conversation/profile_analyzer.py` — RIASEC profile analysis (separate LLM call at temp=0.2)
- `backend/agents/conversation/evidence_accumulator.py` — accumulates RIASEC dimensions + values + region, computes completeness (L1/L2/L3), determines stage transitions
- `backend/agents/conversation/prompts.py` — B2C system prompt template
- `backend/agents/conversation/prompts_b2b.py` — B2B (招生老师视角) prompt variant

## Stage transitions

Evidence-based rules in EvidenceAccumulator:
- OPEN → EXPLORE: trust medium/high OR turns >= 5
- EXPLORE → FOCUS: >= 3 RIASEC dimensions covered + region known
- FOCUS → CONFIRM: >= 4 RIASEC dimensions + >= 1 value
- CONFIRM → DONE: always

## Two separate chat implementations

1. **B2B WebSocket** (`api/routes/chat.py`, `WS /api/v1/chat/session/{session_id}`): Full LangGraph agent with EvidenceAccumulator, profile_analyzer, guard chain, Redis dialog state. Used by the admin dashboard (招生老师端).

2. **C-end Mini-app SSE** (`api/routes/miniapp.py`, `POST /api/v1/chat/messages`): Simpler REST+SSE streaming with RAG retrieval from ChromaDB, sessions persisted in PostgreSQL (`ConsultSession` + `ChatMessage`). Used by the student-facing mini-app. No guards, no LangGraph agent.

## Guard chain

Pluggable guards for anonymous chat sessions (`backend/core/guard.py`). Processed in order; first failure stops the chain. Built-in guards: `ContentLengthGuard` (min 2 chars), `MessageLimitGuard` (20 msg cap), `RateLimitGuard` (Redis-based per-IP). Guards are invoked from the chat route before the LLM call.
