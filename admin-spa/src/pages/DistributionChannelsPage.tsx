import { useEffect, useState } from 'react'
import type { DistributionChannel } from '../types'
import { mockChannels } from '../mock/distribution'
import StatusCard from '../components/StatusCard'
import Modal from '../components/Modal'
import ChannelFormModal from '../components/ChannelFormModal'
import { distributionApi } from '../api/distribution'

export default function DistributionChannelsPage() {
  const [channels, setChannels] = useState<DistributionChannel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<DistributionChannel | null>(null)
  const [message, setMessage] = useState('')

  const [formOpen, setFormOpen] = useState(false)
  const [editingChannel, setEditingChannel] = useState<DistributionChannel | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; error?: string } | null>(null)

  const fetchChannels = () => {
    setLoading(true)
    distributionApi.listChannels(1, 100)
      .then((r) => {
        setChannels(r.data.items ?? [])
        setError(null)
      })
      .catch((e) => {
        setError(e?.message || '获取渠道列表失败')
        setChannels(mockChannels)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchChannels() }, [])

  const handleSave = async (data: { name: string; channel_type: string; webhook_url: string }) => {
    if (editingChannel) {
      await distributionApi.updateChannel(editingChannel.id, data)
      setMessage('渠道已更新')
    } else {
      await distributionApi.createChannel(data)
      setMessage('渠道已创建')
    }
    setFormOpen(false)
    setEditingChannel(null)
    setTestResult(null)
    fetchChannels()
  }

  const handleTest = async () => {
    if (!editingChannel) return
    setTesting(true)
    setTestResult(null)
    try {
      const res = await distributionApi.testChannel(editingChannel.id)
      setTestResult({ ok: res.data.ok, error: res.data.error })
      if (res.data.ok) {
        setChannels((prev) => prev.map((c) => c.id === editingChannel.id ? { ...c, status: 'active', last_test_at: new Date().toISOString() } : c))
      }
    } catch (e: any) {
      setTestResult({ ok: false, error: e?.message || '测试失败' })
    }
    setTesting(false)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await distributionApi.deleteChannel(deleteTarget.id)
      setChannels((prev) => prev.filter((c) => c.id !== deleteTarget.id))
      setMessage('渠道已删除')
    } catch { setMessage('删除失败') }
    setDeleteTarget(null)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>分发渠道</h2>
        <button className="btn btn-primary" onClick={() => { setEditingChannel(null); setFormOpen(true); setTestResult(null) }}>添加渠道</button>
      </div>

      {message && (
        <div className="view-status loading" style={{ marginBottom: 12 }}>
          {message}
          <button className="btn btn-sm btn-secondary" style={{ marginLeft: 8 }} onClick={() => setMessage('')}>×</button>
        </div>
      )}

      <StatusCard loading={loading} error={error} empty={channels.length === 0} emptyMessage="暂无渠道，点击添加渠道配置企业微信群机器人">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
          {channels.map((ch) => (
            <div key={ch.id} className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, marginBottom: 6, opacity: 0.6 }}>🤖</div>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 4px' }}>{ch.name}</h3>
              <div style={{ marginBottom: 8 }}>
                <span className={`pill ${ch.status === 'active' ? 'green' : ch.status === 'error' ? 'red' : ''}`}>
                  {{ active: '正常', inactive: '未激活', error: '异常' }[ch.status] || ch.status}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 4 }}>
                企业微信群机器人
              </div>
              {ch.error_message && (
                <div style={{ fontSize: 11, color: 'var(--color-danger)', marginBottom: 8, padding: '4px 8px', background: '#fef2f2', borderRadius: 4 }}>
                  {ch.error_message}
                </div>
              )}
              {ch.last_test_at && (
                <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 10 }}>
                  上次测试: {new Date(ch.last_test_at).toLocaleString('zh-CN')}
                </div>
              )}
              <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                <button className="btn btn-secondary btn-sm" onClick={() => { setEditingChannel(ch); setFormOpen(true); setTestResult(null) }}>编辑</button>
                <button className="btn btn-secondary btn-sm" onClick={() => setDeleteTarget(ch)} style={{ color: 'var(--color-danger)' }}>删除</button>
              </div>
            </div>
          ))}
        </div>
      </StatusCard>

      <ChannelFormModal
        open={formOpen}
        initial={editingChannel ? { name: editingChannel.name, channel_type: editingChannel.channel_type, webhook_url: '' } : null}
        onSave={handleSave}
        onTest={editingChannel ? handleTest : undefined}
        onCancel={() => { setFormOpen(false); setEditingChannel(null); setTestResult(null) }}
        testResult={testResult}
        testing={testing}
      />

      <Modal
        open={!!deleteTarget}
        title="确认删除"
        message={`确定要删除渠道 "${deleteTarget?.name || ''}" 吗？关联的分发任务将无法执行。`}
        confirmLabel="删除"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
