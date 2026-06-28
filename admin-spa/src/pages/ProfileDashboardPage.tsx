import { useEffect, useState } from 'react'
import api from '../api/client'
import type { ProfileDashboard } from '../types'
import StatusCard from '../components/StatusCard'
import { useMobileStore } from '../stores/mobileStore'

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

export default function ProfileDashboardPage() {
  const isMobile = useMobileStore((s) => s.isMobile)
  const [data, setData] = useState<ProfileDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<ProfileDashboard>('/admin/analytics/profile-dashboard')
      .then((r) => setData(r.data ?? null))
      .catch((e) => {
        setError(e?.message || '获取数据失败')
      })
      .finally(() => setLoading(false))
  }, [])

  const completenessData = data?.completenessBreakdown
  const fullCount = completenessData?.find((c) => c.level === 'L3')?.count ?? 0
  const partialCount = completenessData?.find((c) => c.level === 'L2')?.count ?? 0
  const initialCount = completenessData?.find((c) => c.level === 'L1')?.count ?? 0

  const top3Riasec = (data?.riasecDistribution || [])
    .slice()
    .sort((a, b) => b.avgScore - a.avgScore)
    .slice(0, 3)

  return (
    <div>
      <StatusCard loading={loading} error={error}>
        {data && (
          <>
            <div className="stat-grid" style={{ gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(3,1fr)' }}>
              <div className="stat-card">
                <span className="stat-label">累计画像数</span>
                <span className="stat-value">{data.totalProfiles}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">完整画像数</span>
                <span className="stat-value">{fullCount + partialCount}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">初始画像数</span>
                <span className="stat-value">{initialCount}</span>
              </div>
            </div>

            {/* Top 3 RIASEC interest cards (replaces radar) */}
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-header"><h3>咨询学生画像 Top 3 兴趣</h3></div>
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

            <div className="chart-grid even">
              <div className="card">
                <div className="card-header"><h3>核心价值观分布</h3></div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
                  {data.valuesDistribution.map((v) => (
                    <div key={v.value} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 13, width: 72, flexShrink: 0 }}>{v.value}</span>
                      <div style={{ flex: 1, background: '#e5e9f2', borderRadius: 100, height: 22, overflow: 'hidden' }}>
                        <div style={{ width: `${v.percentage}%`, height: '100%', background: 'var(--color-brand-800)', borderRadius: 100, transition: 'width 0.3s' }} />
                      </div>
                      <span style={{ fontSize: 12, color: 'var(--color-text-muted)', width: 36, textAlign: 'right' }}>{v.percentage}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="stat-grid" style={{ gridTemplateColumns: isMobile ? '1fr' : 'repeat(3,1fr)', marginTop: 20 }}>
              <div className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--color-success)' }}>{fullCount}</div>
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 }}>完整画像（3+ 维度已填充）</div>
              </div>
              <div className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--color-warning)' }}>{partialCount}</div>
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 }}>部分画像（1-2 维度已填充）</div>
              </div>
              <div className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--color-text-muted)' }}>{initialCount}</div>
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 }}>初始画像（仅基础信息）</div>
              </div>
            </div>
          </>
        )}
      </StatusCard>
    </div>
  )
}
