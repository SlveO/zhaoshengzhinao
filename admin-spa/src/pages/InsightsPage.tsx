import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import 'echarts-wordcloud'
import api from '../api/client'
import type { TopicCloudItem, EmotionTimelineData, HotQuestionItem } from '../types'
import StatusCard from '../components/StatusCard'
import PageHeader from '../components/PageHeader'

const EMOTION_COLORS: Record<string, string> = {
  positive: '#52c41a',
  neutral: '#1890ff',
  negative: '#ff4d4f',
  confused: '#faad14',
  anxious: '#ff7a45',
}

const BRAND_COLOR = 'var(--brand-primary)'

export default function InsightsPage() {
  const [topicCloud, setTopicCloud] = useState<TopicCloudItem[] | null>(null)
  const [emotionTimeline, setEmotionTimeline] = useState<EmotionTimelineData | null>(null)
  const [hotQuestions, setHotQuestions] = useState<HotQuestionItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      api.get<TopicCloudItem[]>('/admin/analytics/topic-cloud'),
      api.get<EmotionTimelineData>('/admin/analytics/emotion-timeline'),
      api.get<HotQuestionItem[]>('/admin/analytics/hot-questions'),
    ])
      .then(([tc, em, hq]) => {
        setTopicCloud(tc.data)
        setEmotionTimeline(em.data)
        setHotQuestions(hq.data)
      })
      .catch((e) => setError(e?.message || '获取分析数据失败'))
      .finally(() => setLoading(false))
  }, [])

  const wordCloudOption = {
    tooltip: { show: true },
    series: [
      {
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
            const colors = [
              BRAND_COLOR,
              '#1890ff', '#52c41a', '#faad14', '#ff4d4f',
              '#722ed1', '#13c2c2', '#eb2f96',
            ]
            return colors[Math.floor(Math.random() * colors.length)]
          },
        },
        emphasis: {
          textStyle: { fontSize: 52 },
        },
        data: (topicCloud || []).map((item) => ({
          name: item.word,
          value: item.count,
        })),
      },
    ],
  }

  const emotionOption = {
    tooltip: { trigger: 'axis' },
    legend: {
      data: (emotionTimeline?.timeline || []).map((s) => s.emotion),
      bottom: 0,
    },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: emotionTimeline?.dates || [],
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value', name: '消息数' },
    series: (emotionTimeline?.timeline || []).map((s) => ({
      name: s.emotion,
      type: 'line',
      data: s.data.map((d) => d.count),
      smooth: true,
      lineStyle: { color: EMOTION_COLORS[s.emotion] || undefined },
    })),
  }

  const hotOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 100, right: 40, top: 10, bottom: 20 },
    xAxis: { type: 'value', name: '提及次数' },
    yAxis: {
      type: 'category',
      data: (hotQuestions || []).map((item) => item.topic).reverse(),
      axisLabel: { fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: (hotQuestions || []).map((item) => item.count).reverse(),
        itemStyle: { color: BRAND_COLOR, borderRadius: [0, 4, 4, 0] },
        barMaxWidth: 28,
      },
    ],
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="增强分析"
        subtitle="关键词词云 / 情绪趋势 / 咨询热点"
      />

      <StatusCard loading={loading} error={error}>
        <>
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">关键词词云</h3>
            <StatusCard empty={!topicCloud || topicCloud.length === 0} emptyHint="暂无词云数据，等待更多对话后自动生成。">
              <ReactECharts option={wordCloudOption} style={{ height: 400 }} />
            </StatusCard>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm mt-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">情绪时间线</h3>
            <StatusCard empty={!emotionTimeline || emotionTimeline.timeline.length === 0} emptyHint="暂无情绪数据。">
              <ReactECharts option={emotionOption} style={{ height: 360 }} />
            </StatusCard>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm mt-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">咨询热点 Top-10</h3>
            <StatusCard empty={!hotQuestions || hotQuestions.length === 0} emptyHint="暂无热点数据。">
              <ReactECharts option={hotOption} style={{ height: 400 }} />
            </StatusCard>
          </div>
        </>
      </StatusCard>
    </div>
  )
}
