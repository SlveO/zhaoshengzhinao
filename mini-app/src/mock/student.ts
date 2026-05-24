import type {
  ProfileSnapshot,
  StudentBasicInfo,
  StudentProfileData
} from "@/types/api"

export const mockStudentInfo: StudentBasicInfo = {
  province: "广东",
  subject_type: "物理类",
  score: 585,
  intent_majors: ["计算机", "人工智能"]
}

export const mockProfile: ProfileSnapshot = {
  riasec: {
    R: 4,
    I: 8,
    A: 5,
    S: 4,
    E: 6,
    C: 3
  },
  values: ["技术成长", "就业前景", "城市发展"],
  confidence: 0.76,
  completeness: "L2"
}

export const mockStudentProfileData: StudentProfileData = {
  student: mockStudentInfo,
  profile: mockProfile,
  updated_at: "2026-05-23T10:00:00Z"
}