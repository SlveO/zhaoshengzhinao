import { useState } from 'react'

const SUBJECTS = ['物理+化学+生物', '物理+化学+地理', '物理+生物+地理', '历史+政治+地理', '历史+政治+生物', '历史+地理+化学', '物理+化学+政治', '物理+生物+政治']
const REGIONS = ['广东', '北京', '上海', '浙江', '江苏', '四川', '湖北', '山东', '河南', '湖南']

interface Props {
  onSubmit: (data: { score: number; subjects: string; region: string }) => void
}

export default function WelcomeModal({ onSubmit }: Props) {
  const [score, setScore] = useState('')
  const [subjects, setSubjects] = useState(SUBJECTS[0])
  const [region, setRegion] = useState(REGIONS[0])
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const s = Number(score)
    if (!score || s < 200 || s > 750) {
      setError('请输入有效分数（200-750）')
      return
    }
    onSubmit({ score: s, subjects, region })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
      <div className="relative bg-white rounded-2xl p-6 w-[400px] max-w-[90vw] shadow-xl">
        <h2 className="text-xl font-bold text-text mb-1">欢迎！</h2>
        <p className="text-sm text-muted mb-5">在开始之前，先了解你的基本情况</p>
        {error && <div className="bg-red-50 text-danger text-sm p-3 rounded-lg mb-4">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-muted block mb-1">预估分数</label>
            <input
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="如 610"
              type="number"
              min="200"
              max="750"
              value={score}
              onChange={(e) => { setScore(e.target.value); setError('') }}
              required
            />
          </div>
          <div>
            <label className="text-xs text-muted block mb-1">选科组合</label>
            <select
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-white"
              value={subjects}
              onChange={(e) => setSubjects(e.target.value)}
            >
              {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted block mb-1">所在地区</label>
            <select
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-white"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
            >
              {REGIONS.map((r) => <option key={r}>{r}</option>)}
            </select>
          </div>
          <button type="submit" className="w-full py-2.5 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition">
            开始对话
          </button>
        </form>
      </div>
    </div>
  )
}
