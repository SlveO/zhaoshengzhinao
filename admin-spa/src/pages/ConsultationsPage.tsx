import { useState } from 'react'
import { ListFilter, Calendar } from 'lucide-react'
import BottomSheet from '../components/BottomSheet'

// TODO: replace with API GET /api/consultations
const MOCK_SESSIONS = [
  { id: 'c1', student: '张同学', profile: '广东·物理类', time: '10:24', duration: '8分钟', topic: '计算机专业就业前景咨询', handler: 'AI', status: '已处理' },
  { id: 'c2', student: '李同学', profile: '湖南·历史类', time: '09:15', duration: '15分钟', topic: '师范类选课建议与保研率', handler: '人工', status: '已处理' },
  { id: 'c3', student: '王同学', profile: '江西·物理类', time: '08:50', duration: '5分钟', topic: '学费标准与奖学金政策', handler: 'AI', status: '待处理' },
  { id: 'c4', student: '赵同学', profile: '广东·物理类', time: '昨天 16:20', duration: '12分钟', topic: '电子信息类实验条件咨询', handler: '人工', status: '已处理' },
  { id: 'c5', student: '陈同学', profile: '福建·历史类', time: '昨天 14:05', duration: '7分钟', topic: '法学专业司法考试情况', handler: 'AI', status: '已处理' },
  { id: 'c6', student: '刘同学', profile: '广西·物理类', time: '昨天 11:30', duration: '20分钟', topic: '数据科学就业方向与实习', handler: '人工', status: '已处理' },
  { id: 'c7', student: '周同学', profile: '四川·物理类', time: '前天 15:45', duration: '4分钟', topic: '校园环境和宿舍条件', handler: 'AI', status: '已处理' },
]

const PAGE_SIZE = 5

export default function ConsultationsPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [period, setPeriod] = useState('今天')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [statusSheetOpen, setStatusSheetOpen] = useState(false)
  const [periodSheetOpen, setPeriodSheetOpen] = useState(false)

  const filtered = MOCK_SESSIONS.filter((s) => {
    if (statusFilter && s.status !== statusFilter) return false
    if (search && !s.student.includes(search) && !s.topic.includes(search)) return false
    return true
  })

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageData = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  return (
    <div>
      <div className="search-bar">
        <button
          onClick={() => setStatusSheetOpen(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '7px 12px', border: '1px solid var(--color-border)',
            borderRadius: 8, fontSize: 12, fontFamily: 'inherit',
            background: '#f8fafc', cursor: 'pointer',
            color: statusFilter ? 'var(--color-brand-800)' : 'var(--color-text-secondary)',
            fontWeight: statusFilter ? 600 : 400,
          }}
        >
          <ListFilter size={14} />
          {statusFilter || '全部状态'}
        </button>
        <button
          onClick={() => setPeriodSheetOpen(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '7px 12px', border: '1px solid var(--color-border)',
            borderRadius: 8, fontSize: 12, fontFamily: 'inherit',
            background: '#f8fafc', cursor: 'pointer',
            color: 'var(--color-text-secondary)',
          }}
        >
          <Calendar size={14} />
          {period}
        </button>
        <input
          type="text" placeholder="搜索学生或关键词…"
          value={search} onChange={(e) => { setSearch(e.target.value); setPage(0) }}
        />
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>学生</th><th>时间</th><th>主题摘要</th><th>处理方式</th><th>状态</th>
              </tr>
            </thead>
            <tbody>
              {pageData.map((s) => (
                <tr key={s.id} style={{ cursor: 'pointer' }}>
                  <td>
                    <span style={{ fontWeight: 500 }}>{s.student}</span>
                    <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 1 }}>{s.profile}</div>
                  </td>
                  <td>
                    {s.time}
                    <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 1 }}>{s.duration}</div>
                  </td>
                  <td style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.topic}</td>
                  <td>
                    <span className={`pill${s.handler === 'AI' ? ' pill-blue' : ' pill-amber'}`}>
                      {s.handler === 'AI' ? 'AI 处理' : '人工处理'}
                    </span>
                  </td>
                  <td>
                    <span className={`pill${s.status === '已处理' ? ' pill-green' : ' pill-amber'}`}>
                      {s.status}
                    </span>
                  </td>
                </tr>
              ))}
              {pageData.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 32 }}>
                    暂无咨询记录
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="pagination">
        <span>共 {filtered.length} 条</span>
        <button className="btn btn-secondary btn-sm" disabled={page === 0} onClick={() => setPage(0)}>首页</button>
        <button className="btn btn-secondary btn-sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>上一页</button>
        <span>第 {page + 1}/{totalPages || 1} 页</span>
        <button className="btn btn-secondary btn-sm" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>下一页</button>
      </div>

      <BottomSheet
        open={statusSheetOpen}
        title="咨询状态"
        onClose={() => setStatusSheetOpen(false)}
      >
        {[
          { label: '全部状态', value: '', bg: '#e5e9f2', color: '#64748b' },
          { label: '已处理', value: '已处理', bg: '#dcfce7', color: '#166534' },
          { label: '待处理', value: '待处理', bg: '#fef3c7', color: '#92400e' },
        ].map((opt) => {
          const isActive = statusFilter === opt.value
          return (
            <button
              key={opt.value}
              className="bs-row"
              onClick={() => { setStatusFilter(opt.value); setPage(0); setStatusSheetOpen(false) }}
              style={isActive ? { background: '#f8fafc' } : undefined}
            >
              <div className="bs-row-icon" style={{ background: opt.bg, color: opt.color, fontSize: 14 }}>●</div>
              <span className="bs-row-text" style={isActive ? { fontWeight: 600 } : undefined}>{opt.label}</span>
              {isActive && <span style={{ color: 'var(--color-brand-800)', fontWeight: 600, fontSize: 18 }}>✓</span>}
            </button>
          )
        })}
        <button className="bs-cancel" onClick={() => setStatusSheetOpen(false)}>取消</button>
      </BottomSheet>

      <BottomSheet
        open={periodSheetOpen}
        title="时间范围"
        onClose={() => setPeriodSheetOpen(false)}
      >
        {['今天', '近7天', '近30天'].map((opt) => {
          const isActive = period === opt
          return (
            <button
              key={opt}
              className="bs-row"
              onClick={() => { setPeriod(opt); setPeriodSheetOpen(false) }}
              style={isActive ? { background: '#f8fafc' } : undefined}
            >
              <div className="bs-row-icon" style={{ background: '#dbeafe', color: '#1e40af' }}>
                <Calendar size={20} />
              </div>
              <span className="bs-row-text" style={isActive ? { fontWeight: 600 } : undefined}>{opt}</span>
              {isActive && <span style={{ color: 'var(--color-brand-800)', fontWeight: 600, fontSize: 18 }}>✓</span>}
            </button>
          )
        })}
        <button className="bs-cancel" onClick={() => setPeriodSheetOpen(false)}>取消</button>
      </BottomSheet>
    </div>
  )
}
