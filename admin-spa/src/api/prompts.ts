import api from './client'
import type {
  PromptSummary,
  PromptDetail,
  PromptSaveResponse,
} from '../types/prompt'

/** 列出所有 prompt_key 及当前 active 版本信息 */
export async function listPrompts(): Promise<PromptSummary[]> {
  const resp = await api.get<{ prompts: PromptSummary[] }>('/admin/prompts')
  return resp.data?.prompts ?? []
}

/** 获取单个 prompt 详情（active 内容 + 代码默认值） */
export async function getPrompt(promptKey: string): Promise<PromptDetail> {
  const resp = await api.get<PromptDetail>(`/admin/prompts/${promptKey}`)
  return resp.data
}

/** 保存新版本（触发后端 DB+代码双写） */
export async function savePrompt(
  promptKey: string,
  content: string,
): Promise<PromptSaveResponse> {
  const resp = await api.put<PromptSaveResponse>(
    `/admin/prompts/${promptKey}`,
    { content },
  )
  return resp.data
}

/** 同步所有 prompt_key 的 DB active 内容到代码常量 */
export async function syncPrompts(): Promise<{
  total: number
  success_count: number
  results: Array<{ prompt_key: string; success: boolean; error?: string }>
}> {
  const resp = await api.post('/admin/prompts/sync')
  return resp.data
}
