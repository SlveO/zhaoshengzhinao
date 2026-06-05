import { useState, useEffect } from 'react'

interface ChannelFormData {
  name: string
  channel_type: string
  webhook_url: string
}

interface ChannelFormModalProps {
  open: boolean
  initial?: ChannelFormData | null
  onSave: (data: ChannelFormData) => Promise<void>
  onTest?: () => Promise<void>
  onCancel: () => void
  testResult?: { ok: boolean; error?: string } | null
  testing?: boolean
}

export default function ChannelFormModal({ open, initial, onSave, onTest, onCancel, testResult, testing }: ChannelFormModalProps) {
  const [name, setName] = useState('')
  const [webhookUrl, setWebhookUrl] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open && initial) {
      setName(initial.name)
      setWebhookUrl(initial.webhook_url)
    } else if (open) {
      setName('')
      setWebhookUrl('')
    }
  }, [open, initial])

  if (!open) return null

  const handleSave = async () => {
    if (!name.trim() || !webhookUrl.trim()) return
    setSaving(true)
    try {
      await onSave({ name: name.trim(), channel_type: 'wechat_group', webhook_url: webhookUrl.trim() })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
        <h3>{initial ? '编辑渠道' : '添加渠道'}</h3>

        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>渠道名称</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：2026级新生咨询群"
            style={{
              width: '100%', padding: '8px 12px', border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-input)', fontSize: 13, fontFamily: 'inherit',
              background: 'var(--color-card)',
            }}
          />
        </div>

        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>渠道类型</label>
          <select
            value="wechat_group"
            style={{
              width: '100%', padding: '8px 12px', border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-input)', fontSize: 13, fontFamily: 'inherit',
              background: 'var(--color-card)',
            }}
            disabled
          >
            <option value="wechat_group">企业微信群机器人</option>
          </select>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 2, display: 'block' }}>
            当前版本仅支持企业微信群机器人，更多渠道即将推出
          </span>
        </div>

        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Webhook 地址</label>
          <input
            type="text"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
            style={{
              width: '100%', padding: '8px 12px', border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-input)', fontSize: 12, fontFamily: 'monospace',
              background: 'var(--color-card)',
            }}
          />
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 2, display: 'block' }}>
            在企业微信群里添加群机器人后获取此地址
          </span>
        </div>

        {testResult && (
          <div style={{
            fontSize: 13, padding: '8px 12px', borderRadius: 6, marginBottom: 14,
            background: testResult.ok ? '#f0fdf4' : '#fef2f2',
            color: testResult.ok ? 'var(--color-success)' : 'var(--color-danger)',
          }}>
            {testResult.ok ? '✓ 测试成功，群内已收到测试消息' : `✗ 测试失败: ${testResult.error || '未知错误'}`}
          </div>
        )}

        <div className="btn-group" style={{ justifyContent: 'flex-end', gap: 8 }}>
          {onTest && (
            <button className="btn btn-secondary" onClick={onTest} disabled={testing || !webhookUrl.trim()}>
              {testing ? '测试中...' : '测试连接'}
            </button>
          )}
          <button className="btn btn-secondary" onClick={onCancel}>取消</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving || !name.trim() || !webhookUrl.trim()}>
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
