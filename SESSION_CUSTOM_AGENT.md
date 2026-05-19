# Session D: 可定制 Agent

> 分支: `feat/custom-agent` | 基于: `develop` | 碰 backend + admin-spa

## 启动

```bash
git checkout develop && git checkout -b feat/custom-agent
```

必读: `docs/superpowers/specs/2026-05-19-optimization-design.md` §D

## 任务

### 1. Tenant config 扩展

数据库层面：`tenant.config` JSONB 新增 `ai_persona` 字段（无需 migration）：

```json
{
  "ai_persona": {
    "custom_prompt": "院校自定义的系统提示词...",
    "style": "formal",
    "proactive_recommend": true
  }
}
```

### 2. Chat route prompt 选择 (`backend/api/routes/chat.py`)

在系统提示词构建处加分支：

```python
persona = (tenant_config or {}).get("ai_persona", {})
if persona.get("custom_prompt"):
    system_content = persona["custom_prompt"].format(
        stage=current_stage.value,
        slots_summary=slots_text,
    )
else:
    # Use default B2B prompt
    ...

# Append style hint
style = persona.get("style", "casual")
if style == "formal":
    system_content += "\n\n请使用正式、专业的语气。"
```

### 3. 管理端 persona CRUD (`backend/admin/router.py`)

```python
@router.get("/ai-persona")
async def get_persona(tenant=Depends(get_current_tenant)):
    return tenant.config.get("ai_persona", {})

@router.put("/ai-persona")
async def update_persona(body: dict, tenant=Depends(get_current_tenant), _user=Depends(get_current_tenant_user)):
    # deep merge into tenant.config.ai_persona
    ...
```

### 4. 管理端新页面 (`admin-spa/src/pages/AgentSettingsPage.tsx`)

- 自定义提示词编辑器（textarea, 可用 `{stage}`, `{slots_summary}` 占位符）
- 对话风格选择（正式/亲切）
- 功能开关

## 不碰

- mini-app / analytics

## 完成标志

- [ ] 管理端可编辑 AI persona 并保存
- [ ] 学生端对话使用自定义 persona 生成回复
- [ ] 切换 style 后对话语气有明显变化
