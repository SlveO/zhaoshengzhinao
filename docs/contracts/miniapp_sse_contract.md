# 测试契约：Mini-app SSE 对话端点

> 基于需求规格编写。此文档仅含公开接口和行为契约，不含实现细节。

## 公开接口

```
POST /api/v1/miniapp/chat (SSE)
Headers: X-Tenant: <tenant_slug>
Body: {session_id: str, message: str}
Response: SSE stream (data: {type: "token"|"done", ...})
```

## 行为契约

### SSE 对话响应
- 契约 1：发送消息 → 返回 SSE 流，含 type="done" 事件，done 事件含 assistant_message
- 契约 2：每 3 轮对话 → 触发 profile_bridge，done 事件含 profile_updated: true
- 契约 3：非 3 倍数轮次 → profile_updated: false（仅 regex 提取可能为 true）
- 契约 4：profile_bridge 失败 → 不阻塞 SSE 响应，仅日志 warning，profile_updated 可能仍为 true（如果 regex 提取成功）
- 契约 5：缺少 X-Tenant 头 → 400 错误
- 契约 6：done 事件含 profile_summary 字段（可能为 None）

### profile_updated 字段语义
- `profile_updated = profile_updated_regex OR profile_bridge_ran`
- 契约 1：bridge 成功执行 → profile_bridge_ran=True → profile_updated=True
- 契约 2：bridge 未触发（非 3 倍数） → profile_bridge_ran=False
- 契约 3：bridge 失败 → profile_bridge_ran=False，但 regex 提取可能仍为 True
- 契约 4：bridge 和 regex 都未更新 → profile_updated=False

### profile_bridge 集成点
- 调用时机：assistant 消息保存后，regex 提取前
- 调用条件：`tenant_id 非空 AND should_extract(session_id) == True`
- 参数：`bridge_profile_to_session_profiles(session, tenant_id, user_content, full_content)`
  - full_content = AI 完整回复文本
- 异常处理：try/except 包裹，异常时 logging.warning，不阻塞

## 边界条件
- 空 message、超长 message
- 无效 session_id（不存在）
- 租户隔离：A 租户 session 不被 B 租户访问
- SSE 流中断（客户端断开）
