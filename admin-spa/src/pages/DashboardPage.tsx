import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

const STATS = [
  { label: '累计咨询人数', value: '12,847', change: '+18.2%', up: true },
  { label: '高意向学生', value: '862', change: '+12.5%', up: true },
  { label: '意向转化率', value: '6.7%', change: '+2.1%', up: true },
  { label: '活跃天数', value: '28', change: '本月累计', up: false },
]

export default function DashboardPage() {
  const trendRef = useRef<HTMLDivElement>(null)
  const sourceRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!trendRef.current || !sourceRef.current) return

    const dates = Array.from({ length: 30 }, (_, i) => {
      const d = new Date(); d.setDate(d.getDate() - 29 + i)
      return (d.getMonth() + 1) + '/' + d.getDate()
    })

    const trendChart = echarts.init(trendRef.current)
    trendChart.setOption({
      grid: { left: 40, right: 16, top: 16, bottom: 32 },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0, textStyle: { fontSize: 11 } },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 }, axisTick: { show: false } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#e5e7eb' } } },
      series: [
        {
          name: '咨询量', type: 'line',
          data: Array.from({ length: 30 }, () => Math.floor(200 + Math.random() * 400)),
          smooth: true, symbol: 'none', lineStyle: { color: 'oklch(58% 0.18 255)', width: 2 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'oklch(58% 0.18 255 / 0.12)' }, { offset: 1, color: 'oklch(58% 0.18 255 / 0)' },
          ]) },
        },
        {
          name: '意向数', type: 'line',
          data: Array.from({ length: 30 }, () => Math.floor(30 + Math.random() * 100)),
          smooth: true, symbol: 'none', lineStyle: { color: 'oklch(54% 0.14 155)', width: 2 },
        },
      ],
    })

    const sourceChart = echarts.init(sourceRef.current)
    sourceChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie', radius: ['55%', '80%'], center: ['50%', '48%'], itemStyle: { borderWidth: 0 },
        label: { fontSize: 10 },
        data: [
          { value: 38, name: '广东省' }, { value: 18, name: '湖南省' },
          { value: 14, name: '江西省' }, { value: 12, name: '广西' },
          { value: 10, name: '福建省' }, { value: 8, name: '其他' },
        ],
      }],
    })

    return () => { trendChart.dispose(); sourceChart.dispose() }
  }, [])

  return (
    <div>
      <div className="stat-grid">
        {STATS.map((s) => (
          <div className="stat-card" key={s.label}>
            <span className="stat-label">{s.label}</span>
            <span className="stat-value">{s.value}</span>
            <span className={`stat-change${s.up ? ' up' : ''}`} style={!s.up ? { color: 'var(--muted)' } : undefined}>
              {s.change}
            </span>
          </div>
        ))}
      </div>

      <div className="chart-grid">
        <div className="card">
          <div className="card-header"><h3>咨询趋势 · 近30天</h3><span className="badge">实时</span></div>
          <div ref={trendRef} style={{ height: 260 }} />
        </div>
        <div className="card">
          <div className="card-header"><h3>学生来源分布</h3></div>
          <div ref={sourceRef} style={{ height: 260 }} />
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="card-header" style={{ padding: '20px 24px 0' }}><h3>最近高意向学生</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>学生</th><th>省份</th><th>意向专业</th><th>咨询深度</th><th>最近互动</th><th>状态</th></tr></thead>
            <tbody>
              {[
                ['张*明', '广东', '计算机科学', '深度咨询', '10分钟前', '高意向'],
                ['李*华', '湖南', '电子信息', '表达意向', '1小时前', '高意向'],
                ['王*婷', '江西', '软件工程', '深度咨询', '2小时前', '跟进中'],
                ['陈*杰', '广西', '人工智能', '初步咨询', '3小时前', '待跟进'],
                ['黄*欣', '广东', '数据科学', '表达意向', '5小时前', '高意向'],
              ].map((r, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 500 }}>{r[0]}</td>
                  <td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td>
                  <td style={{ fontSize: 12, color: 'var(--muted)' }}>{r[4]}</td>
                  <td><span className={`pill${r[5] === '高意向' ? ' green' : ' amber'}`}>{r[5]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
