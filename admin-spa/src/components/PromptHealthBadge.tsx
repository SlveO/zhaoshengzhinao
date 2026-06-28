import { useEffect, useState } from 'react'
import { listPrompts } from '../api/prompts'
import type { PromptSummary } from '../types/prompt'

/**
 * 提示词状态徽章。
 * 基于 list 接口的 is_modified 字段统计：DB active 内容与代码默认值的差异。
 * - 全部未修改: 绿色"已同步 (N)"
 * - 有修改: 黄色"X 项已定制"，点击展开详情
 * - 加载中: 灰色"检查中"
 * - 错误: 红色"检查失败"
 */
export default function PromptHealthBadge() {
  const [items, setItems] = useState<PromptSummary[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await listPrompts()
      setItems(list)
    } catch (e) {
      setError(e instanceof Error ? e.message : '检查失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  if (loading) {
    return <span className="health-badge health-badge-loading">检查中...</span>
  }

  if (error) {
    return (
      <span className="health-badge health-badge-error" title={error}>
        检查失败
      </span>
    )
  }

  if (!items || items.length === 0) return null

  const modified = items.filter((i) => i.is_modified)

  if (modified.length === 0) {
    return (
      <span className="health-badge health-badge-ok">
        已同步 ({items.length})
      </span>
    )
  }

  return (
    <span>
      <span
        className="health-badge health-badge-warn"
        onClick={() => setExpanded(!expanded)}
        style={{ cursor: 'pointer' }}
      >
        {modified.length} 项已定制 ▾
      </span>
      {expanded && (
        <div className="health-detail">
          {modified.map((m) => (
            <div key={m.prompt_key} className="health-detail-item">
              <code>{m.prompt_key}</code>
              <span>
                {m.active_version ? `v${m.active_version}` : '未版本化'}
              </span>
            </div>
          ))}
          <button onClick={refresh} className="health-refresh-btn">
            重新检查
          </button>
        </div>
      )}
    </span>
  )
}
