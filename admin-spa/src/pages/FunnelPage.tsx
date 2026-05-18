import { useEffect, useState } from 'react'
import api from '../api/client'
import type { FunnelData } from '../types'
import FunnelChart from '../components/charts/FunnelChart'

export default function FunnelPage() {
  const [data, setData] = useState<FunnelData | null>(null)

  useEffect(() => {
    api.get<FunnelData>('/admin/analytics/funnel').then((r) => setData(r.data))
  }, [])

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        加载中...
      </div>
    )
  }

  if (data._stub) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-gray-800">招生漏斗</h2>
        <FunnelChart
          stages={{ visitors: 0, conversations: 0, deepConsultations: 0, intentExpressed: 0, enrolled: 0 }}
          conversionRates={{}}
        />
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-700">
          暂无数据。当学生开始与小程序对话后，此处将展示招生漏斗转化数据。
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-gray-800">招生漏斗</h2>
      <p className="text-sm text-gray-400">
        {data.period.start} ~ {data.period.end}
      </p>
      <FunnelChart stages={data.stages} conversionRates={data.conversionRates} />
    </div>
  )
}
