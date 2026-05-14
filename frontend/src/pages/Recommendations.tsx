import { useEffect, useState } from 'react'
import { useRecStore } from '../stores/recommendationStore'
import ProfileSummaryBar from '../components/recommendation/ProfileSummaryBar'
import FilterBar from '../components/recommendation/FilterBar'
import RecommendationCard from '../components/recommendation/RecommendationCard'

export default function Recommendations() {
  const { recommendations, profileSnapshot, filters, loading, error, load, setFilter } = useRecStore()
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    load()
  }, [])

  // Show elapsed time while loading
  useEffect(() => {
    if (!loading) { setElapsed(0); return }
    const timer = setInterval(() => setElapsed((t) => t + 1), 1000)
    return () => clearInterval(timer)
  }, [loading])

  const filtered = recommendations.filter((r) => {
    if (filters.level && r.level !== filters.level) return false
    if (filters.city && r.city !== filters.city) return false
    if (filters.category && r.category !== filters.category) return false
    return true
  })

  return (
    <div className="max-w-[900px] mx-auto p-5">
      {profileSnapshot && <ProfileSummaryBar profile={profileSnapshot} />}

      {loading && (
        <div className="flex flex-col items-center justify-center py-16 text-muted">
          <div className="w-10 h-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4" />
          <div className="text-lg font-medium mb-2">正在生成个性化推荐...</div>
          <div className="text-sm">AI 正在基于你的画像分析最匹配的院校和专业</div>
          <div className="text-xs mt-2">已等待 {elapsed} 秒，预计需要 15-30 秒</div>
        </div>
      )}

      {error && !loading && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="text-red-400 text-4xl mb-4">&#9888;</div>
          <div className="text-muted mb-2 text-center max-w-sm">{error}</div>
          <button
            onClick={() => load()}
            className="mt-4 px-6 py-2 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition"
          >
            重试
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="mt-4">
            <FilterBar filters={filters} onChange={setFilter} count={filtered.length} />
          </div>
          <div className="mt-4 space-y-3">
            {filtered.map((r) => (
              <RecommendationCard key={r.rank} rec={r} />
            ))}
            {filtered.length === 0 && (
              <div className="text-center text-muted py-12">没有匹配的推荐结果</div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
