/**
 * MOCK DATA — 仅用于前端展示/演示，与后端无关。
 * 当 API 不可用时，InsightsPage 自动回退到此数据。
 * 后端就绪后直接删除此文件即可，不影响页面逻辑。
 */
import type { TopicCloudItem, EmotionTimelineData, HotQuestionItem } from '../types'

export const mockTopicCloud: TopicCloudItem[] = [
  { word: '录取分数线', count: 156 },
  { word: '王牌专业', count: 142 },
  { word: '就业率', count: 138 },
  { word: '奖学金', count: 125 },
  { word: '校园环境', count: 118 },
  { word: '宿舍条件', count: 110 },
  { word: '转专业', count: 98 },
  { word: '保研率', count: 92 },
  { word: '地理位置', count: 87 },
  { word: '学费', count: 82 },
  { word: '社团活动', count: 76 },
  { word: '实验室', count: 71 },
  { word: '交换项目', count: 65 },
  { word: '招生计划', count: 60 },
  { word: '体检要求', count: 55 },
  { word: '自主招生', count: 48 },
  { word: '提前批', count: 42 },
  { word: '双学位', count: 38 },
  { word: '中外合作', count: 33 },
  { word: '实习基地', count: 28 },
]

export const mockHotQuestions: HotQuestionItem[] = [
  { topic: '贵校今年录取线预计多少分', count: 89 },
  { topic: '计算机专业就业前景如何', count: 76 },
  { topic: '有新生奖学金吗怎么申请', count: 71 },
  { topic: '宿舍是几人间有空调吗', count: 65 },
  { topic: '入学后可以转专业吗', count: 58 },
  { topic: '保研率大概多少', count: 52 },
  { topic: '学校在市区还是郊区', count: 47 },
  { topic: '有国际交流交换机会吗', count: 41 },
  { topic: '体检有视力要求吗', count: 36 },
  { topic: '特殊类型招生怎么报名', count: 30 },
]

function buildDateStrings(days: number): string[] {
  const dates: string[] = []
  const now = new Date()
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    dates.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return dates
}

function randomWalk(days: number, base: number, variance: number): number[] {
  const result: number[] = []
  let v = base
  for (let i = 0; i < days; i++) {
    v = Math.max(0, v + (Math.random() - 0.5) * variance)
    result.push(Math.round(v))
  }
  return result
}

export function mockEmotionTimeline(days = 30): EmotionTimelineData {
  const dates = buildDateStrings(days)
  return {
    dates,
    timeline: [
      { emotion: 'positive', data: randomWalk(days, 45, 20).map((count, i) => ({ date: dates[i], count })) },
      { emotion: 'neutral', data: randomWalk(days, 30, 12).map((count, i) => ({ date: dates[i], count })) },
      { emotion: 'confused', data: randomWalk(days, 15, 10).map((count, i) => ({ date: dates[i], count })) },
      { emotion: 'anxious', data: randomWalk(days, 10, 8).map((count, i) => ({ date: dates[i], count })) },
    ],
  }
}
