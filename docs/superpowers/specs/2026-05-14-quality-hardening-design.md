# 质量加固：Prompt 优化 + 稳定性升级 设计方案

## 一、目标

提升对话智能体的语境贴合度（中国高考场景），并加固系统稳定性（API 重试、超时降级、错误边界、结果缓存），确保真实学生使用时不崩溃。

## 二、Prompt 优化

### 2.1 SYSTEM_PROMPT 改动

**新增中国高考语境段落：**

```
## 学生背景
你面对的是中国高三毕业生。他们刚经历高考，可能处于以下状态：
- 分数焦虑：担心分数不够上理想学校
- 家长期望压力：父母的意愿可能与自己的兴趣冲突
- 信息过载：对大学专业了解有限，容易被热门专业误导
- 同伴比较：同学的选择可能影响自己的判断

理解这些压力，在对话中给予适当的共情和疏导。
```

**新增冲稳保概念提示：**

```
## 志愿策略常识（仅用于对话理解，不给具体建议）
- 冲刺：录取位次略高于学生位次的院校
- 稳妥：录取位次与学生位次接近的院校
- 保底：录取位次明显低于学生位次的院校
```

### 2.2 FEW_SHOT 扩充

当前 3 例 → 扩充为 8 例：

| 类型 | 特征 | 示例话术 |
|------|------|---------|
| 迷茫型 | "不知道喜欢什么" | 换个角度，问时间流逝感 |
| 主见型 | "就想学医" | 追问动机来源 |
| 焦虑型 | "数学不好好烦" | 先共情，再拆分问题 |
| **纠结型** | "爸妈让我学金融但我喜欢历史" | 引导权衡权重 |
| **务实型** | "哪个专业好就业工资高" | 了解价值观后再引导兴趣 |
| **外向型** | "我喜欢和人打交道" | 确认社交场景偏好 |
| **内向型** | "我喜欢一个人安静做事" | 确认独立工作场景 |
| **探索型** | "我对很多东西都好奇但都不深入" | 引导排除法 |

### 2.3 槽位提取优先级

```
优先级 1: LLM <!--SLOTS--> JSON 块（质量最高）
优先级 2: 关键词词典 fallback（稳定兜底）
优先级 3: 保留当前 slots 不变（不做提取）
```

## 三、稳定性加固

### 3.1 DeepSeek API 重试

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def _call_llm(prompt):
    return await llm.ainvoke(prompt)
```

仅对 LLM 调用加重试，其他错误原样抛出。

### 3.2 推荐超时降级

```python
try:
    recs = await asyncio.wait_for(
        generate_recommendations(user_id, profile, db),
        timeout=30
    )
except asyncio.TimeoutError:
    recs = []  # 返回空列表，不含错误信息
    # 日志记录超时
```

### 3.3 推荐结果缓存

```python
# Redis key: recs_cache:{user_id}
# TTL: 10 minutes
# 请求到达时先查缓存，命中直接返回
# 对话有新消息后缓存不失效（10min 自然过期）
```

### 3.4 React ErrorBoundary

```tsx
// 包裹 Chat 和 Recommendations 页面
// 捕获 render 错误，显示降级 UI："页面出现异常，请刷新重试"
// 提供"刷新页面"按钮
```

## 四、修改文件清单

| 文件 | 改动 | 风险 |
|------|------|------|
| `backend/agents/conversation/prompts.py` | 重构 SYSTEM_PROMPT + 8 FEW_SHOT | 低（文本替换） |
| `backend/agents/conversation/agent.py` | 槽位提取优先级调整 | 低 |
| `backend/services/recommendation_service.py` | tenacity 重试 + asyncio 超时 | 中（LLM 调用逻辑） |
| `backend/api/routes/recommendation.py` | Redis 缓存读写 | 低 |
| `backend/requirements.txt` | 加 tenacity | 低 |
| `frontend/src/components/common/ErrorBoundary.tsx` | 新建 | 低 |
| `frontend/src/App.tsx` | ErrorBoundary 包裹路由 | 低 |

## 五、验证方法

1. 冒烟测试：`python scripts/smoke_test.py` 完整 7 轮对话 + 推荐
2. 重试验证：断开网络后观察后端日志出现 retry 信息
3. 超时验证：设置极短超时 → 推荐返回空但不报错
4. 缓存验证：同用户连续两次请求推荐 → 第二次秒级返回
5. ErrorBoundary 验证：故意在 Chat 组件中 throw error → 显示刷新 UI
