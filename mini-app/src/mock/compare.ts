import type { CompareRecommendationsData } from "@/types/api"
import { mockProfile } from "./student"

export const mockCompareRecommendationsData: CompareRecommendationsData = {
  recommendations: [
    {
      tenant_slug: "scnu",
      tenant_name: "华南师范大学",
      match_score: 90,
      majors: [
        {
          college_name: "计算机学院",
          major_name: "人工智能",
          level: "本科",
          province: "广东",
          city: "广州",
          min_rank: 34000,
          min_score: 589,
          subjects: "物理+不限",
          source_url: "https://example.com/admission/scnu-ai"
        },
        {
          college_name: "软件学院",
          major_name: "软件工程",
          level: "本科",
          province: "广东",
          city: "广州",
          min_rank: 38000,
          min_score: 579,
          subjects: "物理+不限",
          source_url: "https://example.com/admission/scnu-se"
        },
        {
          college_name: "计算机学院",
          major_name: "数据科学与大数据技术",
          level: "本科",
          province: "广东",
          city: "广州",
          min_rank: 41000,
          min_score: 573,
          subjects: "物理+不限",
          source_url: "https://example.com/admission/scnu-data"
        }
      ]
    }
  ],
  profile_snapshot: mockProfile,
  tenants_compared: 1
}