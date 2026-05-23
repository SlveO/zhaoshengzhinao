import type {
  PaginationData,
  RecommendationItem
} from "@/types/api"

export const mockRecommendations: RecommendationItem[] = [
  {
    id: "rec_001",
    college_id: "tenant_scnu",
    college_name: "华南师范大学",
    major_name: "人工智能",
    province: "广东",
    city: "广州",
    level: "本科",
    match_score: 92,
    min_score: 589,
    min_rank: 34000,
    subjects: "物理+不限",
    reasons: [
      "该专业与学生的计算机和人工智能兴趣高度匹配",
      "培养方向覆盖机器学习、智能系统与应用开发，适合关注技术成长的学生",
      "近年热度较高，建议结合分数、位次和专业组计划数谨慎评估"
    ],
    risk_level: "reach"
  },
  {
    id: "rec_002",
    college_id: "tenant_scnu",
    college_name: "华南师范大学",
    major_name: "软件工程",
    province: "广东",
    city: "广州",
    level: "本科",
    match_score: 88,
    min_score: 579,
    min_rank: 38000,
    subjects: "物理+不限",
    reasons: [
      "专业方向与编程、系统开发和工程实践兴趣匹配度较高",
      "课程实践性较强，适合希望未来从事软件开发、互联网产品和工程技术岗位的学生",
      "学生当前分数与近年录取区间较接近，可作为本校内较匹配的报考选择"
    ],
    risk_level: "match"
  },
  {
    id: "rec_003",
    college_id: "tenant_scnu",
    college_name: "华南师范大学",
    major_name: "数据科学与大数据技术",
    province: "广东",
    city: "广州",
    level: "本科",
    match_score: 84,
    min_score: 573,
    min_rank: 41000,
    subjects: "物理+不限",
    reasons: [
      "该专业与人工智能、数据分析方向关联度较高，适合对算法和数据应用感兴趣的学生",
      "相比热门人工智能专业，报考风险相对更稳，可作为本校内的稳妥选择",
      "未来可衔接数据分析、智能应用开发、教育科技等方向"
    ],
    risk_level: "safe"
  }
]

export const mockRecommendationsData: PaginationData<RecommendationItem> = {
  items: mockRecommendations,
  total: mockRecommendations.length,
  page: 1,
  page_size: 20
}