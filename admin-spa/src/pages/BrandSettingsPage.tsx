import { useEffect, useState, type FormEvent } from 'react'
import api from '../api/client'
import type { BrandConfig } from '../types'

export default function BrandSettingsPage() {
  const [brand, setBrand] = useState<BrandConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    api.get<BrandConfig>('/admin/brand-config').then((r) => setBrand(r.data))
  }, [])

  const handleSave = async (e: FormEvent) => {
    e.preventDefault()
    if (!brand) return
    setSaving(true)
    setMessage('')
    try {
      await api.put('/admin/brand-config', brand)
      setMessage('保存成功')
      // Re-apply CSS variables
      document.documentElement.style.setProperty('--brand-primary', brand.primaryColor)
      document.documentElement.style.setProperty('--brand-secondary', brand.secondaryColor)
      document.title = `${brand.name} · 管理后台`
    } catch {
      setMessage('保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (!brand) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        加载中...
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-xl font-bold text-gray-800">品牌设置</h2>

      <form onSubmit={handleSave} className="bg-white rounded-xl p-6 shadow-sm space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">院校全称</label>
          <input
            type="text"
            value={brand.name}
            onChange={(e) => setBrand({ ...brand, name: e.target.value })}
            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">院校简称</label>
          <input
            type="text"
            value={brand.shortName}
            onChange={(e) => setBrand({ ...brand, shortName: e.target.value })}
            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">主题色</label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={brand.primaryColor}
                onChange={(e) => setBrand({ ...brand, primaryColor: e.target.value })}
                className="w-10 h-10 rounded-lg border cursor-pointer"
              />
              <input
                type="text"
                value={brand.primaryColor}
                onChange={(e) => setBrand({ ...brand, primaryColor: e.target.value })}
                className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">辅助色</label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={brand.secondaryColor}
                onChange={(e) => setBrand({ ...brand, secondaryColor: e.target.value })}
                className="w-10 h-10 rounded-lg border cursor-pointer"
              />
              <input
                type="text"
                value={brand.secondaryColor}
                onChange={(e) => setBrand({ ...brand, secondaryColor: e.target.value })}
                className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono"
              />
            </div>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Logo URL</label>
          <input
            type="text"
            value={brand.logoUrl}
            onChange={(e) => setBrand({ ...brand, logoUrl: e.target.value })}
            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]"
          />
        </div>

        <div className="p-4 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500 mb-3">预览</p>
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg bg-center bg-contain bg-no-repeat bg-gray-200"
              style={{ backgroundImage: brand.logoUrl ? `url(${brand.logoUrl})` : undefined }}
            />
            <div className="flex gap-2">
              <div className="w-6 h-6 rounded" style={{ background: brand.primaryColor }} />
              <div className="w-6 h-6 rounded" style={{ background: brand.secondaryColor }} />
            </div>
            <span className="text-sm font-medium">{brand.name}</span>
          </div>
        </div>

        {message && (
          <div
            className={`text-sm px-3 py-2 rounded-lg ${
              message.includes('成功') ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-500'
            }`}
          >
            {message}
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2.5 rounded-lg text-white font-medium text-sm transition cursor-pointer disabled:opacity-60"
          style={{ background: 'var(--brand-primary)' }}
        >
          {saving ? '保存中...' : '保存'}
        </button>
      </form>
    </div>
  )
}
