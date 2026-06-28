import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { useMobileStore } from '../stores/mobileStore'

interface ConsultStats {
  total: number
  today_new: number
  pending: number
  processed: number
}

interface ProfileDashboard {
  totalProfiles: number
  monthlyNew: number
  growthRate: number | null
  todayNewSessions: number
  pendingFollowSessions: number
  riasecDistribution: { dimension: string; avgScore: number; count: number }[]
  valuesDistribution: { value: string; percentage: number }[]
  completenessBreakdown: { level: string; count: number }[]
}

interface HotQuestion { topic: string; count: number }

interface ConsultRow {
  session_id: string
  session_string: string
  student_name: string
  province: string
  subjects: string
  score: number
  rank: number | null
  intent_majors: string[]
  consult_summary: string
  consult_started_at: string | null
  follow_status: string
}

export default function DashboardPage() {
  const isMobile = useMobileStore((s) => s.isMobile)
  const [consultStats, setConsultStats] = useState<ConsultStats | null>(null)
  const [profileStats, setProfileStats] = useState<ProfileDashboard | null>(null)
  const [recentConsults, setRecentConsults] = useState<ConsultRow[]>([])
  const [hotQuestions, setHotQuestions] = useState<HotQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [statsRes, profileRes, recentRes, hotRes] = await Promise.allSettled([
          api.get('/admin/consultations/stats/summary'),
          api.get('/admin/analytics/profile-dashboard'),
          api.get('/admin/consultations', { params: { page: 1, page_size: 5 } }),
          api.get('/admin/analytics/hot-questions?days=30'),
        ])
        if (statsRes.status === 'fulfilled') setConsultStats(statsRes.value.data)
        if (profileRes.status === 'fulfilled') setProfileStats(profileRes.value.data)
        if (recentRes.status === 'fulfilled') setRecentConsults(recentRes.value.data?.data || [])
        if (hotRes.status === 'fulfilled') setHotQuestions(hotRes.value.data)
        if (statsRes.status === 'rejected' && profileRes.status === 'rejected') {
          setError('获取数据失败')
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <div style={{ padding: 24, color: '#888' }}>加载中…</div>
  if (error) return <div style={{ padding: 24, color: 'var(--color-danger)' }}>{error}</div>

  const growthRateLabel = profileStats?.growthRate == null
    ? '—'
    : `${profileStats.growthRate > 0 ? '+' : ''}${(profileStats.growthRate * 100).toFixed(1)}%`
  const growthRateColor = profileStats?.growthRate == null
    ? 'var(--color-text-muted)'
    : profileStats.growthRate >= 0 ? '#16a34a' : '#dc2626'

  return (
    <div>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%)',
        borderRadius: 12, padding: isMobile ? '16px 20px' : '24px 28px', marginBottom: isMobile ? 12 : 20,
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <h1 style={{ fontSize: isMobile ? 18 : 22, fontWeight: 700, color: '#fff', margin: '0 0 4px', letterSpacing: '-0.02em' }}>
            招生智脑 · 咨询管理
          </h1>
          <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', margin: 0 }}>
            实时监控咨询会话 · 跟进咨询进度
          </p>
        </div>
      </div>

      {/* 3-column Metric Cards (画像相关已隐藏，与 Sidebar /profile 保持一致) */}
      <div className="stat-grid" style={{ gridTemplateColumns: isMobile ? '1fr' : 'repeat(3,1fr)' }}>
        <div className="stat-card">
          <span className="stat-label">今日新增咨询</span>
          <span className="stat-value">{profileStats?.todayNewSessions ?? 0}</span>
          <span className="stat-detail">
            累计咨询会话 {consultStats?.total ?? 0} 条
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">本月新增咨询</span>
          <span className="stat-value">{profileStats?.monthlyNew ?? 0}</span>
          <span className="stat-detail" style={{ color: growthRateColor }}>
            同比 {growthRateLabel}
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">待跟进会话</span>
          <span className="stat-value">{consultStats?.pending ?? 0}</span>
          <span className="stat-detail">
            已处理 {consultStats?.processed ?? 0} 条
          </span>
        </div>
      </div>

      {/* 画像相关卡片已隐藏：学生画像总数、Top 3 RIASEC 兴趣、价值观分布、画像完整度分布 */}

      {/* Hot questions (单列展示) */}
      <div className="card" style={{ marginTop: isMobile ? 12 : 16 }}>
        <div style={{ marginBottom: 12, fontSize: 14, fontWeight: 600 }}>咨询热点 Top 10</div>
        {hotQuestions.length > 0 ? (
          <div style={{ padding: 16 }}>
            {hotQuestions.slice(0, 10).map((q, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f3f4f6', fontSize: 13 }}>
                <span>{i + 1}. {q.topic}</span>
                <span style={{ color: '#666' }}>{q.count}</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: 32, color: '#999', textAlign: 'center' }}>暂无数据</div>
        )}
      </div>

      {/* Recent consultations */}
      <div className="card" style={{ marginTop: isMobile ? 12 : 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>最近咨询会话</h3>
          <Link to="/consultations" style={{ fontSize: 12, color: 'var(--color-brand-800)', textDecoration: 'none' }}>
            查看全部 →
          </Link>
        </div>

        {recentConsults.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 13 }}>
            暂无咨询会话
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>学生</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>省份</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>选科</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>分数</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>位次</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>咨询摘要</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>状态</th>
                </tr>
              </thead>
              <tbody>
                {recentConsults.map((c) => (
                  <tr key={c.session_id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '10px 12px' }}>{c.student_name}</td>
                    <td style={{ padding: '10px 12px' }}>{c.province || '—'}</td>
                    <td style={{ padding: '10px 12px' }}>{c.subjects || '—'}</td>
                    <td style={{ padding: '10px 12px' }}>{c.score || '—'}</td>
                    <td style={{ padding: '10px 12px' }}>{c.rank ?? '—'}</td>
                    <td style={{ padding: '10px 12px', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {c.consult_summary || '—'}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <StatusBadge status={c.follow_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string; bg: string }> = {
    pending: { label: '待跟进', color: '#d97706', bg: '#fef3c7' },
    processed: { label: '已处理', color: '#16a34a', bg: '#dcfce7' },
    ignored: { label: '已忽略', color: '#6b7280', bg: '#f3f4f6' },
  }
  const cfg = map[status] || map.pending
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 100,
      fontSize: 11,
      fontWeight: 500,
      color: cfg.color,
      background: cfg.bg,
    }}>
      {cfg.label}
    </span>
  )
}
