# 测试契约：分析看板数据消费

> 基于需求规格编写。此文档仅含公开接口和行为契约，不含实现细节。

## 公开接口

```
GET /api/v1/analytics/topic-cloud
GET /api/v1/analytics/profile-dashboard
GET /api/v1/analytics/region-distribution
```

## 行为契约

### topic_cloud
- 数据源 1：chat_messages 表中的消息文本（普通词频，权重 x1）
- 数据源 2：session_profiles.profile_json->'concerns'（权重 x2）
- 契约 1：session_profiles.concerns 有数据 → concerns 词频权重 x2
- 契约 2：concerns 为空 → 仅返回普通词频（权重 x1）
- 契约 3：concerns 数组长度为 0 或 NULL → 跳过（不报错）
- 契约 4：返回 Top N 词汇（按词频排序）
- 契约 5：租户隔离，只返回当前租户数据
- 契约 6：concerns 中的每个词被拆分后加权（jsonb_array_elements_text）

### profile_dashboard
- 契约 1：session_profiles 有数据 → 返回画像汇总（RIASEC 雷达 + 价值观分布 + 完整度分布）
- 契约 2：无数据 → 返回空结构（不报错）
- 契约 3：租户隔离
- 契约 4：completeness 字段分布（L1/L2/L3 计数）

### region_distribution
- 契约 1：session_profiles.profile_json.region_pref 有数据 → 返回地域分布
- 契约 2：无数据 → 返回空结构
- 契约 3：租户隔离

## 边界条件
- session_profiles 表为空
- profile_json 字段缺失或为 NULL
- concerns 为非 list 类型（JSON 解析异常）
- region_pref 为 NULL 或缺少 province/city 键
- 多租户数据隔离验证
