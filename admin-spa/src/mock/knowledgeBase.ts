/**
 * MOCK DATA — 仅用于前端展示/演示，与后端无关。
 * 当 API 不可用时，KnowledgeSettingsPage 自动回退到此数据。
 * 后端就绪后直接删除此文件即可，不影响页面逻辑。
 */
import type { DocumentItem } from '../types'

export const mockDocuments: DocumentItem[] = [
  { id: 'kb-001', title: '2025年各省录取分数线汇总', data_type: 'admission_score', year: 2025, indexed_at: '2026-05-15T10:30:00Z' },
  { id: 'kb-002', title: '2026年招生章程', data_type: 'admission_score', year: 2026, indexed_at: '2026-05-16T08:00:00Z' },
  { id: 'kb-003', title: '计算机科学与技术专业培养方案', data_type: 'curriculum', year: 2025, indexed_at: '2026-05-14T14:20:00Z' },
  { id: 'kb-004', title: '电子信息工程课程大纲', data_type: 'curriculum', year: 2026, indexed_at: '2026-05-17T09:15:00Z' },
  { id: 'kb-005', title: '2025届毕业生就业质量报告', data_type: 'employment', year: 2025, indexed_at: '2026-05-10T16:45:00Z' },
  { id: 'kb-006', title: '校企合作实习基地一览', data_type: 'employment', year: 2026, indexed_at: '2026-05-18T11:00:00Z' },
  { id: 'kb-007', title: '2025年毕业生平均薪资统计', data_type: 'employment', year: 2025, indexed_at: '2026-05-12T13:30:00Z' },
  { id: 'kb-008', title: '校园生活指南', data_type: 'campus_life', year: 2026, indexed_at: '2026-05-19T10:00:00Z' },
  { id: 'kb-009', title: '学生社团与课外活动介绍', data_type: 'campus_life', year: 2026, indexed_at: null },
  { id: 'kb-010', title: '新生入学常见问题 FAQ', data_type: 'campus_life', year: 2026, indexed_at: null },
  { id: 'kb-011', title: '2024年各省专业录取位次', data_type: 'admission_score', year: 2024, indexed_at: '2026-05-13T15:10:00Z' },
  { id: 'kb-012', title: '商学院 MBA 课程设置', data_type: 'curriculum', year: 2025, indexed_at: '2026-05-20T07:45:00Z' },
]
