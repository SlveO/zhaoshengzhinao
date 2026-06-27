import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import * as echarts from 'echarts'
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

const RIASEC_NAMES: Record<string, string> = {
  R: '实用型', I: '研究型', A: '艺术型', S: '社会型', E: '企业型', C: '常规型',
}

const RIASEC_MAJORS: Record<string, string> = {
  R: '机械/电气/土木',
  I: '计算机/人工智能/数据科学',
  A: '设计/传媒/中文',
  S: '师范/心理学/社会工作',
  E: '工商管理/市场营销/金融',
  C: '会计/统计学/档案学',
}

export default function DashboardPage() {
  const isMobile = useMobileStore((s) => s.isMobile)
  const [consultStats, setConsultStats] = useState<ConsultStats | null>(null)
  const [profileStats, setProfileStats] = useState<ProfileDashboard | null>(null)
  const [recentConsults, setRecentConsults] = useState<ConsultRow[]>([])
  const [hotQuestions, setHotQuestions] = useState<HotQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const valuesRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [statsRes, profileRes, recentRes, hotRes] = await Promise.allSettled([
          api.get('/admin/consultations/stats/summary'),
          api.get('/admin/analytics/profile-dashboard'),
          api.get('/admin/consultations', { params: { page: 1, page_size: 5 } }),
          api.get('/admin/analytics/hot-questions?days=7'),
        ])
        if (statsRes.status === 'fulfilled') setConsultStats(statsRes.value.data)
        if (profileRes.status === 'fulfilled') setProfileStats(profileRes.value.data)
        if (recentRes.status === 'fulfilled') setRecentConsults(recentRes.value.data?.data || [])
        if (hotRes.status === 'fulfilled') setHotQuestions(hotRes.value.data)
        if (statsRes.status === 'rejected' && profileRes.status === 'rejected') {
          setError('获取数据失败')
        }
      } catch (e: any) {
        setError(e?.message || '加载失败')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  useEffect(() => {
    if (!valuesRef.current || !profileStats?.valuesDistribution?.length) return
    const chart = echarts.init(valuesRef.current)
    chart.setOption({
      grid: { left: 80, right: 40, top: 10, bottom: 20 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: profileStats.valuesDistribution.map((v) => v.value).reverse(), axisLabel: { fontSize: 12 } },
      series: [{
        type: 'bar',
        data: profileStats.valuesDistribution.map((v) => v.percentage).reverse(),
        itemStyle: { color: '#1a3a6b', borderRadius: [0, 4, 4, 0] },
        barMaxWidth: 24,
      }],
    })
    return () => chart.dispose()
  }, [profileStats])

  if (loading) return <div style={{ padding: 24, color: '#888' }}>加载中…</div>
  if (error) return <div style={{ padding: 24, color: 'var(--color-danger)' }}>{error}</div>

  const growthRateLabel = profileStats?.growthRate == null
    ? '—'
    : `${profileStats.growthRate > 0 ? '+' : ''}${(profileStats.growthRate * 100).toFixed(1)}%`
  const growthRateColor = profileStats?.growthRate == null
    ? 'var(--color-text-muted)'
    : profileStats.growthRate >= 0 ? '#16a34a' : '#dc2626'

  const top3Riasec = (profileStats?.riasecDistribution || [])
    .slice()
    .sort((a, b) => b.avgScore - a.avgScore)
    .slice(0, 3)

  const fullCount = profileStats?.completenessBreakdown?.find((c) => c.level === 'L3')?.count ?? 0
  const partialCount = profileStats?.completenessBreakdown?.find((c) => c.level === 'L2')?.count ?? 0
  const initialCount = profileStats?.completenessBreakdown?.find((c) => c.level === 'L1')?.count ?? 0

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
            实时监控咨询会话 · 跟进学生画像
          </p>
        </div>
      </div>

      {/* 4-column Metric Cards */}
      <div className="stat-grid">
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
        <div className="stat-card">
          <span className="stat-label">学生画像总数</span>
          <span className="stat-value">{profileStats?.totalProfiles ?? 0}</span>
          <span className="stat-detail">
            含 RIASEC + 价值观 + 兴趣维度
          </span>
        </div>
      </div>

      {/* Top 3 RIASEC interest cards */}
      <div className="card" style={{ marginTop: isMobile ? 12 : 16 }}>
        <div style={{ marginBottom: 12, fontSize: 14, fontWeight: 600 }}>咨询学生画像 Top 3 兴趣</div>
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3,1fr)', gap: 12, padding: 16 }}>
          {top3Riasec.length === 0 ? (
            <div style={{ color: '#999', padding: 16 }}>暂无画像数据</div>
          ) : top3Riasec.map((r) => (
            <div key={r.dimension} style={{ padding: 16, background: '#f9fafb', borderRadius: 8, border: '1px solid #f3f4f6' }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#1a3a6b' }}>
                {r.dimension} {RIASEC_NAMES[r.dimension] || ''}
              </div>
              <div style={{ fontSize: 12, color: '#666', margin: '4px 0' }}>学生数 {r.count}</div>
              <div style={{ fontSize: 11, color: '#999' }}>推荐匹配: {RIASEC_MAJORS[r.dimension] || '-'}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Values distribution + Hot questions */}
      <div className="chart-grid even" style={{ marginTop: isMobile ? 12 : 16 }}>
        <div className="card">
          <div style={{ marginBottom: 12, fontSize: 14, fontWeight: 600 }}>价值观分布</div>
          <div ref={valuesRef} style={{ height: isMobile ? 260 : 340 }} />
        </div>
        <div className="card">
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
      </div>

      {/* Completeness breakdown */}
      <div className="stat-grid" style={{ gridTemplateColumns: isMobile ? '1fr' : 'repeat(3,1fr)', marginTop: isMobile ? 12 : 16 }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--color-success)' }}>{fullCount}</div>
          <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>完整画像（L3）</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--color-warning)' }}>{partialCount}</div>
          <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>部分画像（L2）</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 32, fontWeight: 700, color: '#999' }}>{initialCount}</div>
          <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>初始画像（L1）</div>
        </div>
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
