import { useState } from 'react'
import type { Recommendation } from '../../types'
import { recApi } from '../../services/recommendation'

const barColors: Record<string, string> = {
  admission_probability: 'bg-warning',
  interest_match: 'bg-success',
  career_prospect: 'bg-primary',
}

const categoryStyle: Record<
  string,
  { bar: string; bg: string; text: string }
> = {
  '冲刺': { bar: 'bg-danger', bg: 'bg-red-50', text: 'text-danger' },
  '稳妥': {
    bar: 'bg-success',
    bg: 'bg-green-50',
    text: 'text-[#2e7d32]',
  },
  '保底': {
    bar: 'bg-primary',
    bg: 'bg-blue-50',
    text: 'text-primary',
  },
}

export default function RecommendationCard({ rec }: { rec: Recommendation }) {
  const [open, setOpen] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const cs = categoryStyle[rec.category] || categoryStyle['稳妥']

  return (
    <div className="bg-white rounded-xl border border-border overflow-hidden">
      <div className="flex">
        <div className={`w-1 flex-shrink-0 ${cs.bar}`} />
        <div className="flex-1 p-5">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex gap-2 items-center flex-wrap">
                <h3 className="font-bold text-text">{rec.college_name}</h3>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-semibold ${cs.bg} ${cs.text}`}
                >
                  {rec.category}
                </span>
                <span className="text-xs bg-blue-50 text-primary px-2 py-0.5 rounded-full">
                  {rec.level}
                </span>
              </div>
              <div className="font-semibold text-text mt-1.5">
                {rec.major_name}
              </div>
            </div>
            <div className="text-right">
              <div className={`text-2xl font-extrabold ${cs.text}`}>
                {rec.match_score}%
              </div>
              <div className="text-xs text-muted">综合匹配</div>
            </div>
          </div>
          <div className="flex gap-4 mt-4">
            {Object.entries(rec.scores).map(([k, v]) => (
              <div key={k} className="flex-1">
                <div className="flex justify-between text-xs text-muted mb-1">
                  <span>
                    {k === 'admission_probability'
                      ? '录取概率'
                      : k === 'interest_match'
                        ? '兴趣匹配'
                        : '前景评分'}
                  </span>
                  <span>{v}%</span>
                </div>
                <div className="h-1 bg-border rounded-full">
                  <div
                    className={`h-1 rounded-full ${barColors[k] || 'bg-primary'}`}
                    style={{ width: `${v}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <button
            onClick={() => setOpen(!open)}
            className="mt-3 text-primary text-xs hover:underline"
          >
            {open ? '收起' : '展开'}详细理由
          </button>
          {open && (
            <div className="mt-3 bg-gray-50 rounded-lg p-4">
              <div className="text-xs text-muted mb-2">
                推荐理由 & 数据来源
              </div>
              <div className="space-y-3">
                {rec.reasons.map((r, i) => (
                  <div key={i} className="flex gap-2 text-sm">
                    <span className="flex-shrink-0">
                      {r.type === 'score_match'
                        ? '\u{1F3AF}'
                        : r.type === 'interest_match'
                          ? '\u{1F52C}'
                          : '\u{1F4C8}'}
                    </span>
                    <div>
                      <p className="text-text leading-relaxed">{r.content}</p>
                      <p className="text-xs text-muted mt-0.5">
                        来源：{r.source}
                        {r.source_url ? ` (${r.source_url})` : ''}
                        {r.confidence
                          ? ` 置信度: ${r.confidence}`
                          : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* Feedback buttons */}
          {!feedback && (
            <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100">
              <button
                onClick={() => { recApi.submitFeedback(rec.college_name, rec.major_name, 'useful'); setFeedback('useful') }}
                className="text-xs px-3 py-1 rounded-full bg-green-50 text-green-600 hover:bg-green-100 transition"
              >
                👍 有用
              </button>
              <button
                onClick={() => { recApi.submitFeedback(rec.college_name, rec.major_name, 'not_relevant'); setFeedback('not_relevant') }}
                className="text-xs px-3 py-1 rounded-full bg-gray-50 text-gray-500 hover:bg-gray-100 transition"
              >
                👎 不相关
              </button>
            </div>
          )}
          {feedback === 'useful' && (
            <div className="text-xs text-green-600 mt-2">已标记为有用</div>
          )}
          {feedback === 'not_relevant' && (
            <div className="text-xs text-gray-400 mt-2">已标记为不相关</div>
          )}
        </div>
      </div>
    </div>
  )
}
