# Prompt B: Execute Data Pipeline Fixes

## Role
You are the lead developer. Use subagents for all work. Do NOT write code directly.

## Input
Read docs/data-pipeline-task.md for the complete error specification.

## Available Subagents
- backend-dev: Backend Python/FastAPI changes
- admin-spa-dev: Admin dashboard React/TypeScript changes
- mini-app-dev: Student-facing Vue3/uni-app changes
- cmd-executor: Run commands (docker, curl, pytest, seed scripts)
- code-reviewer: Review changes for correctness and safety
- codebase-scanner: Explore codebase for impact analysis

## Workflow

### Error 1: 403 on Insights Pages
1. codebase-scanner: Verify root cause in create_scnu_tenant.py
2. backend-dev: Add topic_cloud/emotion_timeline/hot_questions to scripts/create_scnu_tenant.py
3. cmd-executor: Run the script to update SCNU tenant
4. cmd-executor: curl verify 200 on all 3 analytics endpoints
5. code-reviewer: Review the diff

### Error 2: Knowledge Base Shows 0 Documents
1. codebase-scanner: Check chroma_data volume + TenantData table
2. cmd-executor: Seed knowledge data if needed
3. backend-dev: Fix seed script if modifications needed
4. cmd-executor: Trigger reindex, verify index-status > 0
5. code-reviewer: Review any code changes

### Error 3: Mini-app Status Position
1. codebase-scanner: Find thinking/status rendering in chat component
2. mini-app-dev: Move status into assistant message bubble
3. cmd-executor: Rebuild mini-app Docker image + restart
4. cmd-executor: Verify with Playwright screenshot
5. code-reviewer: Review the diff

## Output
After completing all fixes, produce reports/data-pipeline-fix-report.md with:
1. Error #, root cause confirmed?, fix (file+line), verification result
2. Before/after: test counts, API codes, UI behavior
3. Issues encountered and resolution
4. Remaining work

## Rules
- NEVER use Write/Edit tools. Use Bash heredoc for file creation.
- Run docker compose build + docker compose up -d after any code change.
- Verify each fix before moving to next error.
- Max 2 retries per step if subagent fails.
