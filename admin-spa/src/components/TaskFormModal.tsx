import { useState, useEffect } from 'react'
import FileUpload from './FileUpload'
import type { DistributionFile, DistributionChannel } from '../types'
import { distributionApi } from '../api/distribution'

interface TaskFormData {
  name: string
  file_id: string
  channel_id: string
  schedule_type: string
  schedule_config: Record<string, any>
  scheduled_at: string
  message_text: string
}

interface TaskFormModalProps {
  open: boolean
  initial?: Partial<TaskFormData> | null
  files: DistributionFile[]
  channels: DistributionChannel[]
  onSave: (data: TaskFormData) => Promise<void>
  onCancel: () => void
}

export default function TaskFormModal({ open, initial, files, channels, onSave, onCancel }: TaskFormModalProps) {
  const [name, setName] = useState('')
  const [fileId, setFileId] = useState('')
  const [channelId, setChannelId] = useState('')
  const [scheduleType, setScheduleType] = useState('once')
  const [hour, setHour] = useState(9)
  const [minute, setMinute] = useState(0)
  const [weekDays, setWeekDays] = useState<number[]>([])
  const [monthDay, setMonthDay] = useState(1)
  const [dateTime, setDateTime] = useState('')
  const [messageText, setMessageText] = useState('')
  const [saving, setSaving] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<DistributionFile | null>(null)

  useEffect(() => {
    if (open && initial) {
      if (initial.name) setName(initial.name)
      if (initial.file_id) setFileId(initial.file_id)
      if (initial.channel_id) setChannelId(initial.channel_id)
      if (initial.schedule_type) setScheduleType(initial.schedule_type)
      if (initial.schedule_config) {
        setHour(initial.schedule_config.hour || 9)
        setMinute(initial.schedule_config.minute || 0)
        setWeekDays(initial.schedule_config.days || [])
        setMonthDay(initial.schedule_config.day || 1)
      }
      if (initial.scheduled_at) setDateTime(initial.scheduled_at.slice(0, 16))
      if (initial.message_text) setMessageText(initial.message_text)
    } else if (open) {
      setName('')
      setFileId('')
      setChannelId('')
      setScheduleType('once')
      setHour(9)
      setMinute(0)
      setWeekDays([])
      setMonthDay(1)
      setDateTime('')
      setMessageText('')
      setUploadedFile(null)
      setShowUpload(false)
    }
  }, [open, initial])

  if (!open) return null

  const handleSave = async () => {
    if (!name.trim() || !fileId || !channelId) return
    setSaving(true)
    try {
      const scheduleConfig: Record<string, any> = {}
      let scheduledAt = ''

      if (scheduleType === 'daily') {
        scheduleConfig.hour = hour
        scheduleConfig.minute = minute
      } else if (scheduleType === 'weekly') {
        scheduleConfig.days = weekDays
        scheduleConfig.hour = hour
        scheduleConfig.minute = minute
      } else if (scheduleType === 'monthly') {
        scheduleConfig.day = monthDay
        scheduleConfig.hour = hour
        scheduleConfig.minute = minute
      }
      if (dateTime) {
        scheduledAt = new Date(dateTime).toISOString()
      }

      await onSave({
        name: name.trim(),
        file_id: fileId,
        channel_id: channelId,
        schedule_type: scheduleType,
        schedule_config: scheduleConfig,
        scheduled_at: scheduledAt,
        message_text: messageText.trim() || '',
      })
    } finally {
      setSaving(false)
    }
  }

  const handleFileUploaded = (info: { id: string; original_filename: string; file_size: number; mime_type: string | null }) => {
    setUploadedFile(info as DistributionFile)
    setFileId(info.id)
    setShowUpload(false)
  }

  const weekDayOptions = [
    { value: 0, label: '一' }, { value: 1, label: '二' }, { value: 2, label: '三' },
    { value: 3, label: '四' }, { value: 4, label: '五' }, { value: 5, label: '六' }, { value: 6, label: '日' },
  ]

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520, maxHeight: '85vh', overflowY: 'auto' }}>
        <h3>{initial ? '编辑任务' : '新建任务'}</h3>

        {/* Name */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>任务名称</label>
          <input
            type="text" value={name} onChange={(e) => setName(e.target.value)}
            placeholder="例如：华师2026招生简章推送"
            style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)', fontSize: 13, fontFamily: 'inherit', background: 'var(--color-card)' }}
          />
        </div>

        {/* File */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>选择文件</label>
          {showUpload ? (
            <FileUpload
              onUploaded={handleFileUploaded}
              onUploadStart={async (file) => {
                const res = await distributionApi.uploadFile(file)
                return res.data
              }}
            />
          ) : (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <select
                value={fileId}
                onChange={(e) => setFileId(e.target.value)}
                style={{ flex: 1, padding: '8px 12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)', fontSize: 13, fontFamily: 'inherit', background: 'var(--color-card)' }}
              >
                <option value="">-- 选择已上传文件 --</option>
                {files.map((f) => (
                  <option key={f.id} value={f.id}>{f.original_filename} ({(f.file_size / 1024).toFixed(0)}KB)</option>
                ))}
                {uploadedFile && !files.find((f) => f.id === uploadedFile.id) && (
                  <option value={uploadedFile.id}>{uploadedFile.original_filename}</option>
                )}
              </select>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowUpload(true)}>上传新文件</button>
            </div>
          )}
        </div>

        {/* Channel */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>目标渠道</label>
          <select
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)', fontSize: 13, fontFamily: 'inherit', background: 'var(--color-card)' }}
          >
            <option value="">-- 选择渠道 --</option>
            {channels.filter((c) => c.status === 'active').map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        {/* Schedule type */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>发送方式</label>
          <div style={{ display: 'flex', gap: 8 }}>
            {['once', 'daily', 'weekly', 'monthly'].map((t) => (
              <button
                key={t}
                className={`btn btn-sm ${scheduleType === t ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setScheduleType(t)}
              >
                {{ once: '一次性', daily: '每天', weekly: '每周', monthly: '每月' }[t]}
              </button>
            ))}
          </div>
        </div>

        {/* Schedule config */}
        {scheduleType !== 'once' && (
          <div style={{ marginBottom: 14, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            {scheduleType === 'weekly' && (
              <div style={{ display: 'flex', gap: 4 }}>
                {weekDayOptions.map((d) => (
                  <button
                    key={d.value}
                    className={`btn btn-sm ${weekDays.includes(d.value) ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setWeekDays((prev) => prev.includes(d.value) ? prev.filter((x) => x !== d.value) : [...prev, d.value])}
                    style={{ minWidth: 32, textAlign: 'center' }}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            )}
            {scheduleType === 'monthly' && (
              <select
                value={monthDay}
                onChange={(e) => setMonthDay(Number(e.target.value))}
                style={{ padding: '6px 10px', border: '1px solid var(--color-border)', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', background: 'var(--color-card)' }}
              >
                {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                  <option key={d} value={d}>每月 {d} 号</option>
                ))}
              </select>
            )}
            <span style={{ fontSize: 13 }}>时间</span>
            <select
              value={hour}
              onChange={(e) => setHour(Number(e.target.value))}
              style={{ padding: '6px 10px', border: '1px solid var(--color-border)', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', background: 'var(--color-card)' }}
            >
              {Array.from({ length: 24 }, (_, i) => i).map((h) => (
                <option key={h} value={h}>{String(h).padStart(2, '0')}</option>
              ))}
            </select>
            <span>:</span>
            <select
              value={minute}
              onChange={(e) => setMinute(Number(e.target.value))}
              style={{ padding: '6px 10px', border: '1px solid var(--color-border)', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', background: 'var(--color-card)' }}
            >
              {[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map((m) => (
                <option key={m} value={m}>{String(m).padStart(2, '0')}</option>
              ))}
            </select>
          </div>
        )}

        {scheduleType === 'once' && (
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>发送时间</label>
            <input
              type="datetime-local"
              value={dateTime}
              onChange={(e) => setDateTime(e.target.value)}
              style={{ padding: '8px 12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)', fontSize: 13, fontFamily: 'inherit', background: 'var(--color-card)' }}
            />
          </div>
        )}

        {/* Message text */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>附带消息（可选）</label>
          <textarea
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            placeholder="发送文件时附带的消息..."
            rows={3}
            style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-input)', fontSize: 13, fontFamily: 'inherit', background: 'var(--color-card)', resize: 'vertical' }}
          />
        </div>

        <div className="btn-group" style={{ justifyContent: 'flex-end', gap: 8 }}>
          <button className="btn btn-secondary" onClick={onCancel}>取消</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving || !name.trim() || !fileId || !channelId}>
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
