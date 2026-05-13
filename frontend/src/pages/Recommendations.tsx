import { useEffect } from 'react'
import { useRecStore } from '../stores/recommendationStore'
import ProfileSummaryBar from '../components/recommendation/ProfileSummaryBar'
import FilterBar from '../components/recommendation/FilterBar'
import RecommendationCard from '../components/recommendation/RecommendationCard'

export default function Recommendations() {
  const {
    recommendations,
    profileSnapshot,
    filters,
    loading,
    load,
    setFilter,
  } = useRecStore()

  useEffect(() => {
    load()
  }, [])

  const filtered = recommendations.filter((r) => {
    if (filters.level && r.level !== filters.level) return false
    if (
      filters.city &&
      !r.college_name.includes(filters.city) &&
      !r.college_name.includes(filters.city.replace('市', ''))
    )
      return false
    if (filters.category && r.category !== filters.category) return false
    return true
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        加载中...
      </div>
    )
  }

  return (
    <div className="max-w-[900px] mx-auto p-5">
      <ProfileSummaryBar profile={profileSnapshot} />
      <div className="mt-4">
        <FilterBar
          filters={filters}
          onChange={setFilter}
          count={filtered.length}
        />
      </div>
      <div className="mt-4 space-y-3">
        {filtered.map((r) => (
          <RecommendationCard key={r.rank} rec={r} />
        ))}
        {filtered.length === 0 && (
          <div className="text-center text-muted py-12">
            没有匹配的推荐结果
          </div>
        )}
      </div>
    </div>
  )
}
