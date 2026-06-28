/** 提示词模板 DTO（与后端 /api/v1/admin/prompts 响应对齐） */

/** GET /admin/prompts 列表项 */
export interface PromptSummary {
  prompt_key: string
  active_version: number | null
  has_db_record: boolean
  is_modified: boolean
  updated_at: string | null
}

/** GET /admin/prompts/{prompt_key} 详情 */
export interface PromptDetail {
  prompt_key: string
  active_version: number | null
  content: string
  code_default: string
  is_modified: boolean
  updated_at: string | null
}

/** PUT /admin/prompts/{prompt_key} 保存响应 */
export interface PromptSaveResponse {
  prompt_key: string
  version: number
  is_active: boolean
  sync_success: boolean
}

/** prompt_key 中文标签映射（用于 UI 展示） */
export const PROMPT_KEY_LABELS: Record<string, string> = {
  consult_system: '咨询模块 - 系统提示词',
  consult_intent: '咨询模块 - 意图抽取',
  consult_degraded: '咨询模块 - 降级重生成',
  b2b_system: '推荐模块 - 系统提示词',
  b2b_few_shot: '推荐模块 - Few-shot 示例',
}

/** 各 prompt_key 的简短描述（编辑器顶部说明） */
export const PROMPT_KEY_DESCRIPTIONS: Record<string, string> = {
  consult_system: '咨询模块主回答的 system prompt。控制回答风格、数据引用规则、输出格式。',
  consult_intent: '从用户消息抽取意图（intent_type/majors/province/year）的 prompt。返回 JSON。',
  consult_degraded: '校验失败后的降级重生成 prompt。强制逐条陈述数据表，禁止归纳。',
  b2b_system: '推荐模块主回答的 system prompt。控制对话风格、阶段引导、数据引用规则、输出格式。',
  b2b_few_shot: '推荐模块 Few-shot 示例（JSON 数组）。用于 LLM in-context learning，控制不同类型学生的回复风格。',
}
