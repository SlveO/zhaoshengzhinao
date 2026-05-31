# Session State

## Rule
After context compression or when starting a new task, read `.claude/SESSION_STATE.md` FIRST — before any exploration or action. This is your working memory.

## Update protocol (single-writer)
Only the MAIN agent writes to SESSION_STATE.md. Sub-agents report findings back to the main agent via their result — the main agent then updates the file.

Update the file after:
- Completing a task step → update Progress checkboxes
- Finding a non-obvious bug → add to Discoveries
- Making a design tradeoff → add to Decisions
- Creating/modifying files → update Files table
- Encountering a blocker → update Current Task blocker field

## Sub-agent pattern
When launching sub-agents via the Agent tool, inject relevant SESSION_STATE context into their prompt:
"Current session context: task=X, phase=Y, key files=[...], discoveries=[...]"

Sub-agents should NOT read or write SESSION_STATE.md directly.

## Failure handling
Two distinct failure types — handle differently:

**Permission block (auto mode classifier / HARD BLOCK):**
- Record to `reports/block.md` in Chinese (timestamp, blocked action, target file, suggested manual command)
- Notify user: "操作被权限阻断，详情见 reports/block.md"
- Do NOT retry with sub-agents or alternative tools

**Tool execution error (model capability: InputValidationError, malformed call, etc.):**
- Opus/Haiku retries the same tool call up to 3 times with corrections
- If still failing, spawn Sonnet sub-agent to retry up to 2 times
- If all retries fail, record to reports/block.md

## Cleanup
When all tasks complete, promote lasting Discoveries/Decisions to auto-memory, then delete SESSION_STATE.md.

Keep all entries terse — this file is for agents, not humans.
