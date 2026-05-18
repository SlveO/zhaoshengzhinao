import ReactECharts from 'echarts-for-react'

interface RadarChartProps {
  data: { dimension: string; avgScore: number; count: number }[]
  title?: string
}

export default function RadarChart({ data, title }: RadarChartProps) {
  const option = {
    tooltip: {
      trigger: 'item',
    },
    radar: {
      indicator: data.map((d) => ({
        name: d.dimension,
        max: 10,
      })),
      center: ['50%', '55%'],
      radius: '65%',
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: data.map((d) => d.avgScore),
            name: title || '画像分布',
            areaStyle: { color: 'var(--brand-primary)', opacity: 0.15 },
            lineStyle: { color: 'var(--brand-primary)' },
            itemStyle: { color: 'var(--brand-primary)' },
          },
        ],
      },
    ],
  }

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-800 mb-2">{title || 'RIASEC 画像分布'}</h3>
      {data.length > 0 ? (
        <ReactECharts option={option} style={{ height: 360 }} />
      ) : (
        <div className="flex items-center justify-center h-80 text-gray-400 text-sm">
          暂无数据
        </div>
      )}
    </div>
  )
}
