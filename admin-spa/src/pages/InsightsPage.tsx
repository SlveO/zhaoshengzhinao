import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import 'echarts-wordcloud'
import api from '../api/client'
import type { TopicCloudItem, EmotionTimelineData, HotQuestionItem } from '../types'
import { mockTopicCloud, mockHotQuestions, mockEmotionTimeline } from '../mock/insights'
import StatusCard from '../components/StatusCard'

const EMOTION_COLORS: Record<string, string> = {
  positive: 'oklch(54% 0.14 155)',
  neutral: 'oklch(54% 0.012 250)',
  negative: 'oklch(52% 0.19 25)',
  confused: 'oklch(62% 0.14 85)',
  anxious: 'oklch(55% 0.18 45)',
}

const ACCENT = 'oklch(58% 0.18 255)'

export default function InsightsPage() {
  const [topicCloud, setTopicCloud] = useState<TopicCloudItem[] | null>(null)
  const [emotionTimeline, setEmotionTimeline] = useState<EmotionTimelineData | null>(null)
  const [hotQuestions, setHotQuestions] = useState<HotQuestionItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.allSettled([
      api.get<TopicCloudItem[]>(`/admin/analytics/topic-cloud?days=${days}`),
      api.get<EmotionTimelineData>(`/admin/analytics/emotion-timeline?days=${days}`),
      api.get<HotQuestionItem[]>(`/admin/analytics/hot-questions?days=${days}`),
    ]).then(([tc, em, hq]) => {
      const rejected = [tc, em, hq].filter((r) => r.status === 'rejected')
      if (rejected.length === 3) {
        const firstErr = (rejected[0] as PromiseRejectedResult).reason
        setError(firstErr?.message || '获取分析数据失败')
        setTopicCloud(mockTopicCloud)
        setHotQuestions(mockHotQuestions)
        setEmotionTimeline(mockEmotionTimeline(days))
        return
      }
      if (tc.status === 'fulfilled') setTopicCloud(tc.value.data)
      if (em.status === 'fulfilled') setEmotionTimeline(em.value.data)
      if (hq.status === 'fulfilled') setHotQuestions(hq.value.data)
    }).finally(() => setLoading(false))
  }, [days])

  const wordCloudOption = {
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      sizeRange: [14, 48],
      rotationRange: [-45, 45],
      gridSize: 8,
      drawOutOfBound: false,
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color() {
          const colors = [ACCENT, 'oklch(56% 0.14 230)', 'oklch(54% 0.10 200)', 'oklch(60% 0.08 180)', 'oklch(55% 0.14 220)', 'oklch(52% 0.12 240)', 'oklch(58% 0.10 190)', 'oklch(56% 0.16 210)']
          return colors[Math.floor(Math.random() * colors.length)]
        },
      },
      emphasis: { textStyle: { fontSize: 52 } },
      data: (topicCloud || []).map((item) => ({ name: item.word, value: item.count })),
    }],
  }

  const hotOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 100, right: 40, top: 10, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: (hotQuestions || []).map((item) => item.topic).reverse(),
      axisLabel: { fontSize: 12 },
    },
    series: [{
      type: 'bar',
      data: (hotQuestions || []).map((item) => item.count).reverse(),
      itemStyle: { color: ACCENT, borderRadius: [0, 4, 4, 0] },
      barMaxWidth: 28,
    }],
  }

  const emotionOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: (emotionTimeline?.timeline || []).map((s) => s.emotion), bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: emotionTimeline?.dates || [], axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value' },
    series: (emotionTimeline?.timeline || []).map((s) => ({
      name: s.emotion,
      type: 'line',
      data: s.data.map((d) => d.count),
      smooth: true,
      symbol: 'none',
      lineStyle: { color: EMOTION_COLORS[s.emotion], width: 2 },
    })),
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 20 }}>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>时间范围</span>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={{ padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', background: 'var(--surface)' }}>
          <option value={7}>近7天</option><option value={30}>近30天</option><option value={90}>近90天</option>
        </select>
      </div>

      <StatusCard loading={loading} error={error}>
        <div className="chart-grid even" style={{ marginBottom: 20 }}>
          <div className="card">
            <div className="card-header"><h3>咨询热点 Top-10</h3></div>
            {hotQuestions && hotQuestions.length > 0 ? (
              <ReactECharts option={hotOption} style={{ height: 340 }} />
            ) : (
              <div className="view-status empty"><span>暂无数据</span></div>
            )}
          </div>
          <div className="card">
            <div className="card-header"><h3>关键词词云</h3></div>
            {topicCloud && topicCloud.length > 0 ? (
              <ReactECharts option={wordCloudOption} style={{ height: 340 }} />
            ) : (
              <div className="view-status empty"><span>暂无词云数据</span></div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3>情绪时间线</h3></div>
          {emotionTimeline && emotionTimeline.timeline.length > 0 ? (
            <ReactECharts option={emotionOption} style={{ height: 300 }} />
          ) : (
            <div className="view-status empty"><span>暂无情绪数据</span></div>
          )}
        </div>
      </StatusCard>
    </div>
  )
}
