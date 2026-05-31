import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import { useMobileStore } from '../stores/mobileStore'

// TODO: replace with API calls when backend ready
const MOCK = {
  channelSummary: {
    todayNewLeads: 8562,
    channels: [
      { name: '官网', count: 2350 },
      { name: '微信公众号', count: 2189 },
      { name: '微信小程序', count: 2015 },
      { name: '线下宣讲会', count: 2017 },
    ],
  },
  consultationSummary: {
    total: 1246,
    aiHandled: 842,
    humanHandled: 404,
    avgResponseSeconds: 28,
    trendData: [120, 135, 98, 160, 142, 155, 170, 145, 180, 162, 190, 175],
  },
  intentSummary: { intentScore: 78, highIntent: 642, midIntent: 1284, lowIntent: 2163 },
  followupProgress: { completionRate: 65, pending: 862, inProgress: 1246, done: 2318 },
  news: [
    { date: '5月14日', content: '省份高考政策及志愿填报时间汇总已更新', isNew: true },
    { date: '5月13日', content: '计算机学院线上宣讲会报名人数已突破2,000人', isNew: false },
    { date: '5月12日', content: '2025年招生指南电子版已发布', isNew: false },
  ],
  todos: [
    { label: '待分配线索', count: 236 },
    { label: '未跟进提醒（超24小时）', count: 128 },
    { label: '待回访咨询', count: 91 },
  ],
}

export default function DashboardPage() {
  const trendRef = useRef<HTMLDivElement>(null)
  const isMobile = useMobileStore((s) => s.isMobile)

  useEffect(() => {
    if (!trendRef.current) return
    const chart = echarts.init(trendRef.current)
    chart.setOption({
      grid: { left: 0, right: 0, top: 4, bottom: 0 },
      xAxis: { show: false, data: Array(12).fill('') },
      yAxis: { show: false, min: 0 },
      series: [{
        type: 'line', data: MOCK.consultationSummary.trendData,
        smooth: true, symbol: 'none',
        lineStyle: { color: '#1e40af', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(30,64,175,0.1)' },
            { offset: 1, color: 'rgba(30,64,175,0)' },
          ]),
        },
      }],
    })
    return () => chart.dispose()
  }, [])

  return (
    <div>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%)',
        borderRadius: 12, padding: isMobile ? '16px 20px' : '28px 32px', marginBottom: isMobile ? 12 : 20,
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', right: -20, top: -20,
          opacity: 0.04, fontSize: isMobile ? 48 : 96, fontWeight: 900,
          color: '#fff', letterSpacing: 8, lineHeight: 1,
        }}>
          ADMISSIONS
        </div>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <h1 style={{ fontSize: isMobile ? 18 : 24, fontWeight: 700, color: '#fff', margin: '0 0 4px', letterSpacing: '-0.02em' }}>
            高校招生运营工作台
          </h1>
          <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            · 生源转化闭环 ·
          </p>
        </div>
      </div>

      {/* 4-column Metric Cards */}
      <div className="stat-grid">
        {/* Channel Summary */}
        <div className="stat-card">
          <span className="stat-label">渠道汇总 · 今日</span>
          <span className="stat-value">{MOCK.channelSummary.todayNewLeads.toLocaleString()}</span>
          <span className="stat-detail">新增线索</span>
          <div style={{ display: 'flex', gap: 6, marginTop: 4, fontSize: 11, color: 'var(--color-text-muted)' }}>
            {MOCK.channelSummary.channels.map((c) => (
              <span key={c.name}>{c.name} {c.count.toLocaleString()}</span>
            ))}
          </div>
        </div>

        {/* Consultation Summary */}
        <div className="stat-card">
          <span className="stat-label">咨询承接 · 今日</span>
          <span className="stat-value">{MOCK.consultationSummary.total.toLocaleString()}</span>
          <span className="stat-detail">
            AI {MOCK.consultationSummary.aiHandled} · 人工 {MOCK.consultationSummary.humanHandled} · 均 {MOCK.consultationSummary.avgResponseSeconds}s
          </span>
          <div ref={trendRef} style={{ height: isMobile ? 36 : 44, marginTop: 4 }} />
        </div>

        {/* Intent Score */}
        <div className="stat-card">
          <span className="stat-label">意向识别 · 今日</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ position: 'relative', width: 56, height: 56 }}>
              <svg viewBox="0 0 56 56" style={{ width: 56, height: 56, transform: 'rotate(-90deg)' }}>
                <circle cx="28" cy="28" r="22" stroke="#e5e9f2" strokeWidth="6" fill="none" />
                <circle cx="28" cy="28" r="22" stroke="#22c55e" strokeWidth="6" fill="none"
                  strokeDasharray={`${MOCK.intentSummary.intentScore * 1.38} ${138 - MOCK.intentSummary.intentScore * 1.38}`}
                  strokeLinecap="round" />
              </svg>
              <div style={{
                position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
                fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)',
              }}>
                {MOCK.intentSummary.intentScore}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--color-brand-800)', fontWeight: 500 }}>
                高意向 {MOCK.intentSummary.highIntent.toLocaleString()}
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                中 {MOCK.intentSummary.midIntent.toLocaleString()} · 低 {MOCK.intentSummary.lowIntent.toLocaleString()}
              </div>
            </div>
          </div>
        </div>

        {/* Followup Progress */}
        <div className="stat-card">
          <span className="stat-label">跟进进度 · 今日</span>
          <span className="stat-value">{MOCK.followupProgress.completionRate}%</span>
          <div className="progress-bar" style={{ marginTop: 4 }}>
            <div className="progress-fill" style={{ width: `${MOCK.followupProgress.completionRate}%` }} />
          </div>
          <span className="stat-detail">
            待跟进 {MOCK.followupProgress.pending} · 跟进中 {MOCK.followupProgress.inProgress} · 已完成 {MOCK.followupProgress.done}
          </span>
        </div>
      </div>

      {/* Bottom 2-column */}
      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: isMobile ? 10 : 16 }}>
        {/* News */}
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>招生动态</h3>
          {MOCK.news.map((n, i) => (
            <div key={i} style={{
              display: 'flex', gap: 8, alignItems: 'baseline',
              padding: '8px 0', borderBottom: i < MOCK.news.length - 1 ? '1px solid var(--color-border)' : 'none',
              fontSize: 13,
            }}>
              {n.isNew && (
                <span style={{
                  background: 'var(--color-brand-800)', color: '#fff',
                  padding: '1px 6px', borderRadius: 3, fontSize: 9, fontWeight: 600,
                }}>
                  NEW
                </span>
              )}
              <span style={{ color: 'var(--color-text-muted)', fontSize: 12, flexShrink: 0 }}>{n.date}</span>
              <span style={{ color: 'var(--color-text-primary)' }}>{n.content}</span>
            </div>
          ))}
        </div>

        {/* Todos */}
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>待办提醒</h3>
          {MOCK.todos.map((t, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '10px 0', borderBottom: i < MOCK.todos.length - 1 ? '1px solid var(--color-border)' : 'none',
            }}>
              <span style={{ fontSize: 13 }}>{t.label}</span>
              <span style={{
                background: 'var(--color-danger)', color: '#fff',
                padding: '3px 12px', borderRadius: 100,
                fontSize: 13, fontWeight: 600, fontVariantNumeric: 'tabular-nums',
              }}>
                {t.count}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
