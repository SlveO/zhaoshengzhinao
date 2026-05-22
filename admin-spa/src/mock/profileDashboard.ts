/**
 * MOCK DATA — 仅用于前端展示/演示，与后端无关。
 * 当 API 不可用时，ProfileDashboardPage 自动回退到此数据。
 * 后端就绪后直接删除此文件即可，不影响页面逻辑。
 */
import type { ProfileDashboard } from '../types'

export const mockProfileDashboard: ProfileDashboard = {
  totalProfiles: 2847,
  riasecDistribution: [
    { dimension: '现实型 R', avgScore: 62, count: 1823 },
    { dimension: '研究型 I', avgScore: 78, count: 2140 },
    { dimension: '艺术型 A', avgScore: 55, count: 1430 },
    { dimension: '社会型 S', avgScore: 70, count: 1950 },
    { dimension: '企业型 E', avgScore: 66, count: 1780 },
    { dimension: '常规型 C', avgScore: 58, count: 1510 },
  ],
  valuesDistribution: [
    { value: '成就导向', percentage: 32 },
    { value: '社会贡献', percentage: 25 },
    { value: '稳定保障', percentage: 18 },
    { value: '创新突破', percentage: 15 },
    { value: '自由独立', percentage: 10 },
  ],
  completenessBreakdown: [
    { level: 'L3', count: 1560 },
    { level: 'L2', count: 890 },
    { level: 'L1', count: 397 },
  ],
  _stub: true,
}
