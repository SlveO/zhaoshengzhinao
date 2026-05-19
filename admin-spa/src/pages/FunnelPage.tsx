import { useEffect, useState } from 'react'
import api from '../api/client'
import type { FunnelData } from '../types'
import FunnelChart from '../components/charts/FunnelChart'
import StatusCard from '../components/StatusCard'
import PageHeader from '../components/PageHeader'

export default function FunnelPage() {
  const [data, setData] = useState<FunnelData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<FunnelData>('/admin/analytics/funnel')
      .then((r) => setData(r.data))
      .catch((e) => setError(e?.message || '获取数据失败'))
  }, [])

  return (
    <div className="space-y-4">
      <PageHeader
        title="招生漏斗"
        subtitle={data && !data._stub ? `${data.period.start} ~ ${data.period.end}` : undefined}
      />

      <StatusCard loading={!data} error={error} empty={data?._stub} emptyHint="当学生开始与小程序对话后，此处将展示招生漏斗转化数据。">
        <FunnelChart stages={data!.stages} conversionRates={data!.conversionRates} />
      </StatusCard>
    </div>
  )
}
