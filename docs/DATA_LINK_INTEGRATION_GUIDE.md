# Data Link Integration Guide

## 1. Module Positioning

The data link module is a development-stage bridge from AI consultation turns to structured student data.

- It currently stores sessions, profiles, and report summaries in local JSON files.
- The JSON store is intentionally replaceable by database tables later.
- The module does not generate AI consultation answers. It runs after the AI reply is produced and extracts structured information from `user_message` and `ai_reply`.

## 2. B Group AI Consultation Integration

Call the data link pipeline after each AI reply is generated:

```python
from services.data_link import process_consultation_turn
from services.data_link_store import JsonDataLinkStore

store = JsonDataLinkStore("data/mock")

result = process_consultation_turn(
    store=store,
    tenant_id="tenant_scnu",
    student_id="stu_xxx",
    session_id="session_xxx",
    user_message="学生输入",
    ai_reply="AI 回复",
)
```

The returned `result` contains:

- `session`: updated chat session and messages.
- `extractedInfo`: fields extracted in this turn.
- `profile`: merged student profile.
- `report`: refreshed report summary.
- `extractionMethod`: `rule`, `llm`, or `rule_fallback`.

## 3. A Group Database Integration

`JsonDataLinkStore` is the current development storage adapter. A database version can replace it by implementing the same methods:

- `get_session`
- `upsert_session`
- `get_profile`
- `upsert_profile`
- `list_profiles`
- `list_sessions`
- `save_report`

Suggested future adapter name:

```python
class DatabaseDataLinkStore:
    ...
```

The core extraction, profile merge, scoring, tags, and report logic do not need major changes when storage is replaced.

## 4. Current JSON Outputs

Demo output files:

- `data/mock/chat_sessions.json`
- `data/mock/student_profiles.json`
- `data/mock/report_summary.json`

Manual interactive test output files:

- `data/manual_test/chat_sessions.json`
- `data/manual_test/student_profiles.json`
- `data/manual_test/report_summary.json`

`data/manual_test/` is ignored and should not be committed.

## 5. Interactive Manual Testing

Run:

```bash
npm run data-link:interactive
```

Use a different `studentId` for each manual student. Reusing the same `studentId` intentionally merges turns into the same profile.

The script prints:

- current hybrid/LLM mode
- whether an LLM key is found
- extracted fields
- merged profile
- intent score and level
- tags
- report summary

## 6. LLM Configuration

LLM extraction is configured only through environment variables:

```bash
DATA_LINK_LLM_ENABLED=true
DATA_LINK_LLM_PROVIDER=deepseek
DATA_LINK_LLM_API_KEY=your-real-key
DATA_LINK_LLM_BASE_URL=https://api.deepseek.com/v1/chat/completions
DATA_LINK_LLM_MODEL=deepseek-chat
DATA_LINK_LLM_TIMEOUT=20
```

`.env.example` contains example values only. Do not commit real API keys or `.env`.

Default behavior without a key:

- `HybridExtractor` uses rule extraction.
- demo, interactive, and tests continue to run offline.

## 7. Current Limitations

- This is still a development-stage data link.
- JSON files are not a production database and are not intended for concurrent writes.
- LLM output may be unstable, so rule fallback remains required.
- Privacy, permissions, production database migrations, and admin pages belong to later productization work.
