# RAG 接入对话模型 — 技术执行报告

> 发件人: Role D (数据+基础设施) | 收件人: Role A (后端核心) | 日期: 2026-05-23 | 优先级: 中

---

## 1. 背景

华南师范大学 (SCNU) 深度知识库已完成入库与索引，数据覆盖：

| 数据类型 | 记录数 | 内容示例 |
|----------|--------|----------|
| 录取分数 | 1,567 | 各专业历年最低分、位次、选科要求 |
| 培养计划 | 86 | 核心课程、培养目标 |
| 就业报告 | 344 | 就业率、月薪、去向行业 |
| 综合咨询 | 16 | 住宿费、奖学金、转专业政策等 FAQ |

这些数据已向量化存入 ChromaDB 集合 `scnu_colleges`，可通过以下接口检索：

```bash
curl "http://localhost:8000/api/v1/knowledge/search?q=华师计算机录取分&k=5" \
  -H "X-Tenant: scnu"
```

返回结构：

```json
{
  "query": "华师计算机录取分",
  "tenant": "scnu",
  "results": [
    {
      "id": "uuid",
      "text": "计算机科学与技术 2024 广东 最低分...",
      "metadata": { "data_type": "admission_score", "major_name": "计算机科学与技术" },
      "score": 0.87,
      "source_url": "https://..."
    }
  ]
}
```

**当前问题：对话 WebSocket (`/api/v1/chat/session/{id}`) 未调用此接口，LLM 无法获取 SCNU 知识库中的真实数据。**

---

## 2. 需要改动的位置

**文件**: `backend/api/routes/chat.py`
**函数**: `chat_websocket` (第 88 行)
**改动量**: ~15 行，在 LLM 调用前插入一次知识库检索

### 2.1 现有流程 (第 200-235 行)

```
用户消息 → 拼 System Prompt → session_llm.ainvoke(msgs) → 返回
                                 ↑
                          没有检索步骤
```

### 2.2 目标流程

```
用户消息 → search_similar(用户问题, k=5, tenant_slug) → 检索结果注入 System Prompt → LLM → 返回
```

---

## 3. 可用的底层函数

Role D 已提供完整的检索接口，Role A 只需调用一个函数：

### 方式一：HTTP 调用知识库 API (推荐，不引入新依赖)

```python
import httpx
from config import settings

async def search_knowledge(query: str, tenant_slug: str, k: int = 5) -> str:
    """调用知识库 API，返回格式化的检索结果文本。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"http://127.0.0.1:8000/api/v1/knowledge/search",
                params={"q": query, "k": k},
                headers={"X-Tenant": tenant_slug},
            )
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return ""
            lines = ["\n## 知识库检索结果 (仅供参考)"]
            for i, r in enumerate(results[:k], 1):
                lines.append(f"{i}. {r['text']}")
                if r.get("source_url"):
                    lines.append(f"   来源: {r['source_url']}")
            return "\n".join(lines)
    except Exception:
        return ""  # 检索失败不阻断对话
```

### 方式二：直接调 ChromaDB (更快，但耦合知识库模块)

```python
from knowledge_base.chroma_client import search_similar

results = search_similar(
    query=user_content,
    k=5,
    tenant_slug=tenant_slug,  # 已在 chat.py:93 解析
)
```

---

## 4. 具体改动位置

在 `chat.py` 中，**第 230 行 `system_msg = SystemMessage(content=system_content)` 之前**，插入检索逻辑：

```python
# ===== 插入开始 =====
# RAG: 检索租户知识库，注入 System Prompt
if tenant_slug and tenant_slug != "default":
    knowledge_context = await search_knowledge(user_content, tenant_slug, k=5)
    if knowledge_context:
        system_content += knowledge_context
# ===== 插入结束 =====

system_msg = SystemMessage(content=system_content)
msgs = [system_msg] + history

# Step 1: Conversation agent
ai_response = await session_llm.ainvoke(msgs)
```

`tenant_slug` 已在第 93 行通过 WebSocket query params 解析，无需新增变量。

---

## 5. 注意事项

### 5.1 嵌入模型说明

当前 `scnu_colleges` 集合使用 ChromaDB 默认嵌入 (`all-MiniLM-L6-v2`) 自动向量化。中文语义检索可用但非最优。如果后续要升级到 bge-large-zh-v1.5：

- 需要重建索引：Role D 执行 `reindex_tenant("scnu")`，同时修改 `indexer.py:104` 传入 bge embeddings
- 届时检索方式需改为 `search_similar()` (内部用 bge)，而非 ChromaDB 内置 `query_texts`

**当前先用 ChromaDB 内置嵌入即可，功能优先。**

### 5.2 性能

- 知识库 API 调用超时设为 5 秒，失败静默降级（不阻断对话）
- SCNU 集合仅 1,997 条文档，检索延迟 < 100ms
- 检索结果限制 k=5，Token 增量可控

### 5.3 租户隔离

- `tenant_slug="scnu"` 只检索 SCNU 数据
- `tenant_slug="default"` 或无租户时不检索（跳过后面的 B2B 对话不受影响）

---

## 6. 验证方法

```bash
# 1. 确认知识库 API 可访问
curl "http://localhost:8000/api/v1/knowledge/search?q=计算机录取分数&k=3" \
  -H "X-Tenant: scnu"
# 期望: 返回 3 条 SCNU 相关文档

# 2. 启动 WebSocket 对话, 提问 SCNU 相关
# 小程序连接: ws://localhost:8000/api/v1/chat/session/{session_id}?tenant=scnu
# 发送消息: "华南师范大学计算机专业分数线是多少"

# 3. 预期: AI 回复中包含 SCNU 真实录取数据, 而非泛泛回答
```

---

## 7. 文件清单

| 文件 | 归属 | 本次是否改动 |
|------|------|-------------|
| `backend/api/routes/chat.py` | Role A | **需改动 (~15行)** |
| `backend/api/routes/knowledge.py` | Role D | 无需改动 |
| `backend/knowledge_base/chroma_client.py` | Role D | 无需改动 |
| `backend/knowledge/indexer.py` | Role D | 无需改动 |

---

## 8. 后续优化方向 (非本次范围)

- 嵌入模型统一为 bge-large-zh-v1.5，提升中文检索精度
- 检索结果做 rerank，过滤低相关度文档
- 缓存高频检索结果，减少重复调用
- 在 System Prompt 中增加检索结果使用指令 ("如果知识库没有相关信息，直接说不知道")

---

**Role D 侧已全部就绪，等待 Role A 接线。**
