import ReactECharts from 'echarts-for-react'

interface FunnelChartProps {
  stages: {
    visitors: number
    conversations: number
    deepConsultations: number
    intentExpressed: number
    enrolled: number
  }
  conversionRates: Record<string, number>
}

const STAGE_LABELS: Record<string, string> = {
  visitors: '访问',
  conversations: '对话',
  deepConsultations: '深度咨询',
  intentExpressed: '意向表达',
  enrolled: '录取报到',
}

export default function FunnelChart({ stages, conversionRates }: FunnelChartProps) {
  const entries = Object.entries(stages) as [string, number][]
  const data = entries.map(([key, val]) => ({
    name: STAGE_LABELS[key] || key,
    value: val,
  }))

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 人',
    },
    series: [
      {
        type: 'funnel',
        left: '10%',
        top: 20,
        bottom: 20,
        width: '80%',
        min: 0,
        max: Math.max(...data.map((d) => d.value), 1),
        sort: 'descending',
        gap: 2,
        label: { show: true, position: 'inside', formatter: '{b}' },
        labelLine: { length: 10, lineStyle: { width: 1 } },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        emphasis: { label: { fontSize: 16 } },
        data,
      },
    ],
  }

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-800 mb-2">招生漏斗</h3>
      <ReactECharts option={option} style={{ height: 360 }} />
      <div className="grid grid-cols-4 gap-3 mt-4">
        {Object.entries(conversionRates).slice(0, 4).map(([key, rate]) => (
          <div key={key} className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-lg font-bold" style={{ color: 'var(--brand-primary)' }}>
              {(rate * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {key.replace(/([A-Z])/g, ' $1').trim()}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
