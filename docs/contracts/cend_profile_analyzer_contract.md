# 测试契约：C-end Profile Analyzer

> 基于执行计划 B1 字段体系编写。此文档仅含公开接口签名和行为契约，不含实现细节。

## 公开接口（仅签名）

```python
@dataclass
class CendExtractionResult:
    basic: dict           # {province, subject_type, score}
    interests: dict       # {preferred_subjects: list, strong_subjects: list, hobbies: list}
    concerns: list        # 自由标签列表
    riasec: dict          # {R, I, A, S, E, C} 各 0-10
    values: list          # 价值观排序
    region_pref: dict     # {province, city}
    extra: dict           # 其他信息
    completeness: str     # "L1" | "L2" | "L3"

    def to_profile_json(self) -> dict: ...
    def has_any_data(self) -> bool: ...

async def analyze_cend_turn(
    user_msg: str,
    ai_reply: str,
    existing_profile: Optional[dict] = None,
    _conversation_history: Optional[list] = None,
    max_retries: int = 2,
) -> CendExtractionResult: ...

def build_cend_analysis_prompt(
    user_msg: str,
    ai_reply: str,
    existing_profile: Optional[dict],
) -> str: ...

def parse_cend_response(text: str) -> CendExtractionResult: ...

def merge_extraction_results(
    existing: CendExtractionResult,
    new_extraction: CendExtractionResult,
) -> CendExtractionResult: ...

def _compute_completeness(result: CendExtractionResult) -> str: ...  # "L1" | "L2" | "L3"
def _summarize_existing(existing_profile: Optional[dict]) -> str: ...
def _dedup_merge_lists(existing_list: list, new_list: list) -> list: ...
```

## 行为契约

### analyze_cend_turn
- 输入：user_msg + ai_reply + existing_profile(可选) + max_retries
- 输出：CendExtractionResult
- 契约 1：LLM 返回合法 JSON → 返回结构化结果
- 契约 2：LLM 返回非法 JSON → 返回空结果（has_any_data() == False，不抛异常）
- 契约 3：LLM 超时/失败 → 重试 max_retries 次后返回空结果（不抛异常）
- 契约 4：existing_profile 非空 → 新提取应与已有信息合并
- 契约 5：重试使用指数退避（1s → 2s）

### build_cend_analysis_prompt
- 输入：user_msg + ai_reply + existing_profile
- 输出：完整 prompt 字符串
- 契约 1：prompt 包含 7 字段定义说明
- 契约 2：prompt 包含 JSON 输出格式要求
- 契约 3：existing_profile 非空时，prompt 包含已有画像上下文摘要
- 契约 4：prompt 包含 "本轮对话" 段落，含 user_msg 和 ai_reply

### parse_cend_response
- 输入：LLM 响应文本
- 输出：CendExtractionResult
- 契约 1：合法 JSON → 正确解析为 8 字段（含 completeness）
- 契约 2：非法 JSON → 返回空结果（不抛异常）
- 契约 3：JSON 缺少字段 → 缺失字段为默认空值
- 契约 4：JSON 含额外字段 → 忽略额外字段
- 契约 5：RIASEC 值超出范围 → 保留原值（不裁剪）

### merge_extraction_results
- 输入：existing(CendExtractionResult) + new_extraction(CendExtractionResult)
- 输出：合并后的 CendExtractionResult
- 契约 1：list 字段（concerns, values）合并去重，保留顺序（existing 优先）
- 契约 2：scalar 字段（basic, region_pref），new 非空时覆盖 existing
- 契约 3：RIASEC 字段，new 非零值覆盖 existing（0 = "未提及"）
- 契约 4：interests dict 深度合并，各子 list 去重合并
- 契约 5：existing 为空 → 直接返回 new
- 契约 6：completeness 重新计算

### _compute_completeness
- 输入：CendExtractionResult
- 输出："L1" | "L2" | "L3"
- 契约 1：仅 basic 字段有值 → "L1"
- 契约 2：basic + interests + concerns 有值 → "L2"
- 契约 3：basic + interests + concerns + riasec + values 有值 → "L3"
- 契约 4：所有字段空 → "L1"（最低级别）

### CendExtractionResult.to_profile_json
- 输出：dict，含 8 个键（basic/interests/concerns/riasec/values/region_pref/extra/completeness）
- 契约 1：返回的 dict 可 JSON 序列化
- 契约 2：list 字段返回副本（不暴露内部引用）

### CendExtractionResult.has_any_data
- 输出：bool
- 契约 1：所有字段空 → False
- 契约 2：任一字段有数据 → True
- 契约 3：RIASEC 全为 0 → 视为无数据

## 边界条件
- 空字符串输入、超长输入（>10000 字符）、纯标点、多语言混合
- existing_profile 为 None / 空字典 / 部分填充
- RIASEC 值超出 0-10 范围
- LLM 响应包含 markdown 代码块包裹的 JSON
