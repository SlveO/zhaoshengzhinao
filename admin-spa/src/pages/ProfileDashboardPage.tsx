import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import api from '../api/client'
import type { ProfileDashboard } from '../types'
import { mockProfileDashboard } from '../mock/profileDashboard'
import StatusCard from '../components/StatusCard'

export default function ProfileDashboardPage() {
  const [data, setData] = useState<ProfileDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const radarRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get<ProfileDashboard>('/admin/analytics/profile-dashboard')
      .then((r) => setData(r.data ?? null))
      .catch((e) => {
        setError(e?.message || '获取数据失败')
        setData(mockProfileDashboard)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!radarRef.current || !data?.riasecDistribution?.length) return
    const chart = echarts.init(radarRef.current)
    chart.setOption({
      tooltip: {},
      legend: { bottom: 0, data: ['本校学生画像', '全国均值'] },
      radar: {
        indicator: data.riasecDistribution.map((d) => ({ name: d.dimension, max: 100 })),
        center: ['50%', '52%'],
        radius: '65%',
      },
      series: [{
        type: 'radar',
        data: [
          {
            value: data.riasecDistribution.map((d) => d.avgScore),
            name: '本校学生画像',
            areaStyle: { color: 'oklch(58% 0.18 255 / 0.12)' },
            lineStyle: { color: 'oklch(58% 0.18 255)', width: 2 },
            itemStyle: { color: 'oklch(58% 0.18 255)' },
          },
          {
            value: [50, 55, 52, 54, 53, 50],
            name: '全国均值',
            areaStyle: { opacity: 0 },
            lineStyle: { color: '#ccc', width: 1.5, type: 'dashed' },
            itemStyle: { color: '#ccc' },
          },
        ],
      }],
    })
    return () => chart.dispose()
  }, [data])

  const completenessData = data?.completenessBreakdown
  const fullCount = completenessData?.find((c) => c.level === 'L3')?.count ?? 0
  const partialCount = completenessData?.find((c) => c.level === 'L2')?.count ?? 0
  const initialCount = completenessData?.find((c) => c.level === 'L1')?.count ?? 0

  return (
    <div>
      <StatusCard loading={loading} error={error}>
        {data && (
          <>
            <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
              <div className="stat-card">
                <span className="stat-label">累计画像数</span>
                <span className="stat-value">{data.totalProfiles}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">完整画像数</span>
                <span className="stat-value">{fullCount + partialCount}</span>
                <span className="stat-change up">+12%</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">本月新增</span>
                <span className="stat-value">{Math.floor(data.totalProfiles * 0.15)}</span>
                <span className="stat-change up">+8%</span>
              </div>
            </div>

            <div className="chart-grid even">
              <div className="card">
                <div className="card-header"><h3>RIASEC 职业兴趣雷达</h3></div>
                <div ref={radarRef} style={{ height: 340 }} />
              </div>
              <div className="card">
                <div className="card-header"><h3>核心价值观分布</h3></div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
                  {data.valuesDistribution.map((v) => (
                    <div key={v.value} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 13, width: 72, flexShrink: 0 }}>{v.value}</span>
                      <div style={{ flex: 1, background: 'var(--bg)', borderRadius: 100, height: 22, overflow: 'hidden' }}>
                        <div style={{ width: `${v.percentage}%`, height: '100%', background: 'var(--accent)', borderRadius: 100, transition: 'width 0.3s' }} />
                      </div>
                      <span style={{ fontSize: 12, color: 'var(--muted)', width: 36, textAlign: 'right' }}>{v.percentage}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3,1fr)', marginTop: 20 }}>
              <div className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--green)' }}>{fullCount}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>完整画像（3+ 维度已填充）</div>
              </div>
              <div className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--amber)' }}>{partialCount}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>部分画像（1-2 维度已填充）</div>
              </div>
              <div className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--muted)' }}>{initialCount}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>初始画像（仅基础信息）</div>
              </div>
            </div>
          </>
        )}
      </StatusCard>
    </div>
  )
}
