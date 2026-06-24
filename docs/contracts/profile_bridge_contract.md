# 测试契约：Profile Bridge

> 基于执行计划 B2 编写。此文档仅含公开接口签名和行为契约，不含实现细节。

## 公开接口（仅签名）

```python
async def get_chat_message_count(session_id: str) -> int: ...

async def should_extract(session_id: str) -> bool: ...

async def load_existing_profile_json(
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Optional[dict]: ...

async def bridge_profile_to_session_profiles(
    session: ConsultSession,
    tenant_id: uuid.UUID,
    user_content: str,
    assistant_content: str,
) -> bool: ...

def _compute_confidence(result: CendExtractionResult) -> dict: ...
def _ensure_backup_dir() -> None: ...
def _dict_to_extraction_result(data: Optional[dict]) -> CendExtractionResult: ...
```

## 行为契约

### should_extract
- 输入：session_id(str)
- 输出：bool
- 契约 1：消息数 == 0 → 返回 False
- 契约 2：消息数 == 3 → 返回 True（每 3 轮触发）
- 契约 3：消息数 == 6 → 返回 True
- 契约 4：消息数 == 1 或 2 → 返回 False（非 3 的倍数）
- 契约 5：消息数 == 4 或 5 → 返回 False
- 契约 6：DB 查询失败 → 返回 False（不抛异常）

### get_chat_message_count
- 输入：session_id(str)
- 输出：int
- 契约 1：无消息 → 返回 0
- 契约 2：N 条用户消息 → 返回 N
- 契约 3：DB 异常 → 返回 0（不抛异常）

### bridge_profile_to_session_profiles
- 输入：session(ConsultSession) + tenant_id(uuid.UUID) + user_content(str) + assistant_content(str)
- 输出：bool（是否成功更新）
- 契约 1：首次调用 → 创建 session_profiles 记录
- 契约 2：后续调用 → 更新已有记录（merge 模式）
- 契约 3：LLM 提取失败 → 返回 False（不抛异常，不写 DB）
- 契约 4：成功 → 写入 DB + 写入 JSON 备份文件
- 契约 5：此函数永不抛异常（NEVER raise），所有异常被 catch 并返回 False
- 契约 6：assistant_content 参数为 AI 完整回复文本

### load_existing_profile_json
- 输入：tenant_id(uuid.UUID) + session_id(uuid.UUID)
- 输出：Optional[dict]
- 契约 1：记录存在 → 返回 profile_json dict
- 契约 2：记录不存在 → 返回 None
- 契约 3：租户隔离 — tenant_id 不匹配时不返回数据

### _compute_confidence
- 输入：CendExtractionResult
- 输出：dict（含置信度相关信息）
- 契约 1：字段越完整 → 置信度越高
- 契约 2：返回 dict 可 JSON 序列化

### _dict_to_extraction_result
- 输入：Optional[dict]
- 输出：CendExtractionResult
- 契约 1：None 输入 → 返回空 CendExtractionResult
- 契约 2：合法 dict → 转换为 CendExtractionResult
- 契约 3：缺失字段 → 使用默认值

## 边界条件
- session_id 不存在
- tenant_id 不匹配（租户隔离）
- 并发调用同一 session_id
- DB 连接失败
- JSON 备份目录不可写
- ConsultSession 对象字段缺失
