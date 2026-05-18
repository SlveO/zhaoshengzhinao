import { useEffect, useState } from 'react'
import api from '../api/client'
import { useAuthStore } from '../stores/authStore'
import type { BrandConfig } from '../types'

export function useBrandConfig() {
  const [brand, setBrand] = useState<BrandConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const token = useAuthStore((s) => s.token)

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get<BrandConfig>('/admin/brand-config')
      .then((res) => {
        const b = res.data
        setBrand(b)
        if (b.primary_color) {
          document.documentElement.style.setProperty('--brand-primary', b.primary_color)
          document.documentElement.style.setProperty('--sidebar-bg', b.primary_color)
        }
        if (b.secondary_color) {
          document.documentElement.style.setProperty('--brand-secondary', b.secondary_color)
        }
        if (b.logo_url) {
          document.documentElement.style.setProperty('--brand-logo', `url(${b.logo_url})`)
        }
        document.title = b.name ? `${b.name} · 管理后台` : '招生智脑 · 管理后台'
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [token])

  return { brand, loading }
}
