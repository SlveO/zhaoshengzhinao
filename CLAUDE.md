# CLAUDE.md

B2B multi-tenant SaaS for Chinese university admissions ("招生智脑").

See `.claude/rules/` for detailed guidance:
- `quick-start.md` — startup commands, testing, lint, DB
- `architecture.md` — subsystems, middleware chain, tenant model
- `conversation-agent.md` — LangGraph agent, chat implementations, guard chain
- `recommendation.md` — recommendation engine pipeline
- `admin-analytics.md` — event logging, analytics modules
- `miniapp.md` — mini-app tenant builds, SSE + polling
- `conventions.md` — coding conventions (DeepSeek, auth, CORS, API clients)
- `session-state.md` — cross-compression session state, single-writer pattern

## Write/Edit file operations (HARD RULE — always apply)
The Write and Edit tools are UNSTABLE on DeepSeek-backed models (Opus, Haiku). **Never use them directly.**

Instead, use Bash heredoc for ALL file creation:
```bash
cat > filepath << 'ENDOFFILE'
...content exactly as written...
ENDOFFILE
```
For editing, use Bash sed or python3 string replace.

If Bash fails, spawn tool-writer Sonnet sub-agent: `Agent({subagent_type:"tool-writer", model:"sonnet", prompt:"Write file <path> with content: ..."})`. Max 2 retries, then record to reports/block.md.
