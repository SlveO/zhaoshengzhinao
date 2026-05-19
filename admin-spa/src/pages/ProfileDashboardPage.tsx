import { useEffect, useState } from 'react'
import api from '../api/client'
import type { ProfileDashboard } from '../types'
import RadarChart from '../components/charts/RadarChart'
import StatusCard from '../components/StatusCard'
import PageHeader from '../components/PageHeader'

export default function ProfileDashboardPage() {
  const [data, setData] = useState<ProfileDashboard | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<ProfileDashboard>('/admin/analytics/profile-dashboard')
      .then((r) => setData(r.data))
      .catch((e) => setError(e?.message || '获取数据失败'))
  }, [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="画像看板"
        subtitle={data ? `累计画像 ${data.totalProfiles} 人` : undefined}
      />

      <StatusCard loading={!data} error={error}>
        <>
          {data!._stub && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-700 mb-6">
              暂无画像数据。当学生完成对话并生成画像后，此处将展示群体画像分析。
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <RadarChart
              data={data!.riasecDistribution}
              title="RIASEC 画像分布"
            />

            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">价值观分布</h3>
              <StatusCard empty={data!.valuesDistribution.length === 0}>
                <div className="space-y-3">
                  {data!.valuesDistribution.map((v) => (
                    <div key={v.value} className="flex items-center gap-3">
                      <span className="text-sm text-gray-600 w-24 truncate">{v.value}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-5">
                        <div
                          className="h-5 rounded-full transition-all"
                          style={{
                            width: `${v.percentage}%`,
                            background: 'var(--brand-primary)',
                          }}
                        />
                      </div>
                      <span className="text-sm text-gray-500 w-12 text-right">
                        {v.percentage}%
                      </span>
                    </div>
                  ))}
                </div>
              </StatusCard>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">画像完整度</h3>
              <StatusCard empty={data!.completenessBreakdown.length === 0}>
                <div className="grid grid-cols-3 gap-4">
                  {data!.completenessBreakdown.map((c) => (
                    <div key={c.level} className="text-center p-4 bg-gray-50 rounded-lg">
                      <div
                        className="text-2xl font-bold"
                        style={{ color: 'var(--brand-primary)' }}
                      >
                        {c.count}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">{c.level}</div>
                    </div>
                  ))}
                </div>
              </StatusCard>
            </div>
          </div>
        </>
      </StatusCard>
    </div>
  )
}
