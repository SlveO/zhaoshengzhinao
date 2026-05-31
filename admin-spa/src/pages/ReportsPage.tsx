import { useState, useRef, useCallback } from 'react'
import { useMobileStore } from '../stores/mobileStore'
import { Calendar } from 'lucide-react'
import BottomSheet from '../components/BottomSheet'

// TODO: replace with API GET /api/strategy/report?view=
interface ReportEntry {
  rank: number
  title: string
  desc: string
}
interface ActionEntry extends ReportEntry {
  priority: 'P0' | 'P1' | 'P2'
}
interface PerspectiveData {
  concerns: ReportEntry[]
  gaps: ReportEntry[]
  actions: ActionEntry[]
}

const REPORT_DATA: Record<string, PerspectiveData> = {
  weekly: {
    concerns: [
      { rank: 1, title: '就业去向咨询上升', desc: '电子信息类、计算机方向的就业去向持续被追问。' },
      { rank: 2, title: '转专业政策被反复追问', desc: '学生希望知道入校后的调整空间和具体规则。' },
      { rank: 3, title: '电子信息类专业热度提升', desc: '' },
      { rank: 4, title: '家长更关注就读条件', desc: '宿舍、食堂、校园安全等问题明显多于往年。' },
    ],
    gaps: [
      { rank: 1, title: '电子信息类就业案例不足', desc: '现有材料对就业去向、企业类型和岗位说明不够具体。' },
      { rank: 2, title: '转专业政策解释不够直观', desc: '规则入口分散，学生难以快速理解申请条件与流程。' },
      { rank: 3, title: '近三年录取位次入口不明显', desc: '' },
      { rank: 4, title: '专业培养方案缺乏学生化表达', desc: '表述偏行政化，学生和家长理解门槛较高。' },
    ],
    actions: [
      { rank: 1, title: '发布《电子信息类专业就业去向解析》推文', desc: '用真实去向、企业类型和岗位方向回应就业顾虑。', priority: 'P0' },
      { rank: 2, title: '在公众号菜单新增"转专业政策说明"', desc: '把申请条件、时间节点和问题集中呈现。', priority: 'P1' },
      { rank: 3, title: '宣讲会增加"近三年录取位次解读"环节', desc: '', priority: 'P2' },
      { rank: 4, title: '定向广告物料补充专业培养与就业信息', desc: '针对电子信息、计算机等热门专业制作专题页。', priority: 'P2' },
    ],
  },
  content: {
    concerns: [
      { rank: 1, title: '学生对专业课程内容了解不足', desc: '多数学生对"电子信息工程学什么"缺乏基本认知。' },
      { rank: 2, title: '培养方案关键信息缺失', desc: '学生关心辅修、双学位等个性化培养路径。' },
      { rank: 3, title: '师资介绍吸引力不够', desc: '' },
      { rank: 4, title: '国际化学习机会少', desc: '海外交换、联合培养等信息不充分。' },
    ],
    gaps: [
      { rank: 1, title: '缺少"专业课程地图"可视化', desc: '学生想了解四年学习路径，但现有材料以文字为主。' },
      { rank: 2, title: '优秀毕业生案例未充分利用', desc: '校友故事分散在新闻中，未作为招生材料集中展示。' },
      { rank: 3, title: '实验室/科研平台介绍缺乏吸引力', desc: '' },
      { rank: 4, title: '校园文化内容不够生动', desc: '' },
    ],
    actions: [
      { rank: 1, title: '制作交互式"专业课程地图"H5', desc: '把四年课程、实践、实习路径可视化呈现。', priority: 'P0' },
      { rank: 2, title: '整理"校友故事集"专题页', desc: '按专业分类，突出就业和升学成果。', priority: 'P1' },
      { rank: 3, title: '为每个重点实验室拍摄短视频导览', desc: '', priority: 'P2' },
      { rank: 4, title: '开发校园 VR 导览', desc: '', priority: 'P2' },
    ],
  },
  lecture: {
    concerns: [
      { rank: 1, title: '宣讲会内容与线上咨询差异大', desc: '学生在宣讲会上听到的信息与线上咨询不一致。' },
      { rank: 2, title: '家长关注点与预设内容错位', desc: '家长更关心就业和费用，但宣讲以学术介绍为主。' },
      { rank: 3, title: '针对性不足', desc: '' },
      { rank: 4, title: '时间安排不够灵活', desc: '' },
    ],
    gaps: [
      { rank: 1, title: '宣讲缺少问答环节数据分析', desc: '宣讲后的集体问答未系统化为知识库补充。' },
      { rank: 2, title: '不同省份的差异化宣讲策略缺失', desc: '各省份关注点差异大，但宣讲内容统一。' },
      { rank: 3, title: '线下咨询效率偏低', desc: '' },
      { rank: 4, title: '缺乏后续跟进的系统流程', desc: '' },
    ],
    actions: [
      { rank: 1, title: '建立宣讲效果反馈闭环', desc: '每次宣讲后自动分析问答数据，更新宣讲重点。', priority: 'P0' },
      { rank: 2, title: '按省份定制宣讲内容', desc: '基于本省学生咨询数据调整宣讲侧重点。', priority: 'P1' },
      { rank: 3, title: '增设家长专场', desc: '', priority: 'P2' },
      { rank: 4, title: '开发面向家长的决策辅助工具', desc: '', priority: 'P2' },
    ],
  },
  channel: {
    concerns: [
      { rank: 1, title: '官网是学生首选信息渠道', desc: '近7天80%的高意向学生首次接触来自官网。' },
      { rank: 2, title: '小程序日活持续增长', desc: '微信小程序日均访问量超过公众号，成为第二触点。' },
      { rank: 3, title: '宣讲会后官网流量激增', desc: '' },
      { rank: 4, title: '公众号推文打开率下降', desc: '近两周推文打开率从12%降至8%。' },
    ],
    gaps: [
      { rank: 1, title: '官网招生专题页信息密度不足', desc: '学生访问后平均停留仅42秒，关键信息分散在多个页面。' },
      { rank: 2, title: '小程序缺少专业对比功能', desc: '学生频繁在多个专业页面间切换，缺乏横向对比。' },
      { rank: 3, title: '公众号菜单结构陈旧', desc: '' },
      { rank: 4, title: '线下物料与线上信息不同步', desc: '' },
    ],
    actions: [
      { rank: 1, title: '官网招生专题页改版', desc: '将专业介绍、录取数据、就业案例整合为单页专题。', priority: 'P0' },
      { rank: 2, title: '小程序增加专业对比功能', desc: '支持同时选择3个专业进行横向对比。', priority: 'P1' },
      { rank: 3, title: '优化公众号菜单导航', desc: '', priority: 'P2' },
      { rank: 4, title: '建立线上线下渠道内容同步机制', desc: '', priority: 'P2' },
    ],
  },
}

const PERSPECTIVES: Record<string, string> = {
  weekly: '本周总览',
  content: '内容优化',
  lecture: '宣讲重点',
  channel: '渠道建议',
}

const PRIORITY_LABEL: Record<string, { bg: string; color: string }> = {
  P0: { bg: '#fee2e2', color: '#991b1b' },
  P1: { bg: '#fef3c7', color: '#92400e' },
  P2: { bg: '#dbeafe', color: '#1e40af' },
}

const PRIORITY_ORDER = { P0: 0, P1: 1, P2: 2 }

interface Version {
  label: string
  time: string
  data: PerspectiveData
}

export default function ReportsPage() {
  const isMobile = useMobileStore((s) => s.isMobile)
  const [view, setView] = useState('weekly')
  const [reportPeriod, setReportPeriod] = useState('2026年5月')
  const [periodSheetOpen, setPeriodSheetOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [data, setData] = useState<PerspectiveData>(structuredClone(REPORT_DATA.weekly))
  const [showHistory, setShowHistory] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null)
  const dragItem = useRef<{ col: keyof PerspectiveData; idx: number } | null>(null)

  const systemVersion = REPORT_DATA[view]
  const [versions] = useState<Version[]>([
    { label: '系统建议', time: '2026-05-21 09:30', data: REPORT_DATA.weekly },
    { label: '保存记录 #2', time: '2026-05-20 16:15', data: REPORT_DATA.weekly },
    { label: '保存记录 #1', time: '2026-05-19 14:42', data: REPORT_DATA.weekly },
  ])

  const switchView = (k: string) => {
    setView(k)
    setData(structuredClone(REPORT_DATA[k]))
    setEditing(false)
  }

  const updateTitle = (col: keyof PerspectiveData, idx: number, val: string) => {
    setData((prev) => {
      const next = structuredClone(prev)
      ;(next[col] as ReportEntry[])[idx].title = val
      return next
    })
  }

  const updateDesc = (col: keyof PerspectiveData, idx: number, val: string) => {
    setData((prev) => {
      const next = structuredClone(prev)
      ;(next[col] as ReportEntry[])[idx].desc = val
      return next
    })
  }

  const updatePriority = (idx: number, p: 'P0' | 'P1' | 'P2') => {
    setData((prev) => {
      const next = structuredClone(prev)
      next.actions[idx].priority = p
      // Auto-sort by priority: P0 → P1 → P2
      next.actions.sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority])
      next.actions.forEach((item, i) => { item.rank = i + 1 })
      return next
    })
  }

  const addItem = (col: keyof PerspectiveData) => {
    setData((prev) => {
      const next = structuredClone(prev)
      const items = next[col] as ReportEntry[]
      if (col === 'actions') {
        const newAction: ActionEntry = { rank: items.length + 1, title: '新建条目', desc: '', priority: 'P2' }
        ;(items as ActionEntry[]).push(newAction)
        // Re-sort after adding
        ;(items as ActionEntry[]).sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority])
        items.forEach((item, i) => { item.rank = i + 1 })
      } else {
        items.push({ rank: items.length + 1, title: '新建条目', desc: '' })
      }
      return next
    })
  }

  const removeItem = (col: keyof PerspectiveData, idx: number) => {
    setData((prev) => {
      const next = structuredClone(prev)
      ;(next[col] as ReportEntry[]).splice(idx, 1)
      ;(next[col] as ReportEntry[]).forEach((item, i) => { item.rank = i + 1 })
      return next
    })
  }

  const moveItem = useCallback((col: keyof PerspectiveData, from: number, to: number) => {
    setData((prev) => {
      const next = structuredClone(prev)
      const items = next[col] as ReportEntry[]
      const [moved] = items.splice(from, 1)
      items.splice(to, 0, moved)
      items.forEach((item, i) => { item.rank = i + 1 })
      return next
    })
  }, [])

  // Drag handlers
  const onDragStart = (col: keyof PerspectiveData, idx: number) => {
    dragItem.current = { col, idx }
  }

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const onDrop = (col: keyof PerspectiveData, toIdx: number) => {
    const from = dragItem.current
    if (!from || from.col !== col || from.idx === toIdx) return
    moveItem(col, from.idx, toIdx)
    dragItem.current = null
  }

  const selectedData = selectedVersion !== null ? versions[selectedVersion].data : null

  const renderEditableCell = (
    col: keyof PerspectiveData,
    item: ReportEntry | ActionEntry,
    idx: number,
    numberColor: string,
  ) => (
    <div
      key={idx}
      draggable={editing}
      onDragStart={() => onDragStart(col, idx)}
      onDragOver={onDragOver}
      onDrop={() => onDrop(col, idx)}
      style={{
        padding: '10px 0', borderBottom: idx < data[col].length - 1 ? '1px solid #f1f5f9' : 'none',
        cursor: editing ? 'grab' : 'default',
        transition: 'background 0.12s',
      }}
      onMouseEnter={(e) => { if (editing) e.currentTarget.style.background = '#fafbfc' }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
    >
      <div style={{ display: 'flex', gap: 8, alignItems: 'start' }}>
        {/* Drag handle + rank number */}
        <span style={{
          width: 20, height: 20, borderRadius: '50%', background: numberColor,
          color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, fontWeight: 600, flexShrink: 0, marginTop: 1,
        }}>
          {item.rank}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          {'priority' in item && (
            <select
              value={item.priority}
              onChange={(e) => updatePriority(idx, e.target.value as 'P0' | 'P1' | 'P2')}
              disabled={!editing}
              style={{
                fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 8,
                border: editing ? '1px solid #e5e9f2' : 'none',
                background: PRIORITY_LABEL[item.priority].bg,
                color: PRIORITY_LABEL[item.priority].color,
                fontFamily: 'inherit', cursor: editing ? 'pointer' : 'default',
                appearance: 'none', marginBottom: 4,
              }}
            >
              <option>P0</option><option>P1</option><option>P2</option>
            </select>
          )}
          {/* Title */}
          <div
            contentEditable={editing}
            suppressContentEditableWarning
            onBlur={(e) => updateTitle(col, idx, e.currentTarget.textContent || '')}
            style={{
              fontWeight: 600, fontSize: 12, outline: 'none',
              borderBottom: editing ? '1px dashed transparent' : 'none',
              padding: '2px 0', borderRadius: 3,
            }}
            onFocus={(e) => { if (editing) e.currentTarget.style.borderBottomColor = '#bfdbfe' }}
          >
            {item.title}
          </div>
          {/* Description - always render &zwnj; when empty so it's clickable */}
          <div
            contentEditable={editing}
            suppressContentEditableWarning
            onBlur={(e) => {
              const text = e.currentTarget.textContent || ''
              // Strip zero-width space if user left it empty
              updateDesc(col, idx, text.replace(/​/g, ''))
            }}
            style={{
              fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 2,
              outline: 'none', borderBottom: editing ? '1px dashed transparent' : 'none',
              padding: '2px 0', borderRadius: 3, minHeight: editing ? 18 : undefined,
            }}
            onFocus={(e) => {
              if (editing) {
                e.currentTarget.style.borderBottomColor = '#bfdbfe'
                // Insert zero-width space if empty so cursor lands inside
                if (!e.currentTarget.textContent || e.currentTarget.textContent === '') {
                  e.currentTarget.innerHTML = '​'
                }
              }
            }}
          >
            {item.desc || (editing ? '​' : '')}
          </div>
        </div>
        {/* Delete button — always visible in edit mode */}
        {editing && (
          <button
            onClick={() => removeItem(col, idx)}
            className="btn btn-sm"
            style={{
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: '#f5222d', fontSize: 18, padding: '0 4px', lineHeight: 1,
              flexShrink: 0,
            }}
            title="删除此条目"
          >
            ×
          </button>
        )}
      </div>
    </div>
  )

  const renderDiffCell = (item: ReportEntry, versionItem: ReportEntry | null) => (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <div style={{ flex: 1, padding: 8, background: '#fef2f2', borderRadius: 4, fontSize: 11 }}>
          <div style={{ color: '#991b1b', fontWeight: 600, marginBottom: 2, fontSize: 10 }}>当前修改</div>
          <div style={{ fontWeight: 600 }}>{item.title}</div>
          {item.desc && <div style={{ color: '#5a6478', marginTop: 2 }}>{item.desc}</div>}
        </div>
        <div style={{ flex: 1, padding: 8, background: '#f0fdf4', borderRadius: 4, fontSize: 11 }}>
          <div style={{ color: '#166534', fontWeight: 600, marginBottom: 2, fontSize: 10 }}>
            {selectedVersion !== null ? versions[selectedVersion].label : '系统建议'}
          </div>
          {versionItem ? (
            <>
              <div style={{ fontWeight: 600 }}>{versionItem.title}</div>
              {versionItem.desc && <div style={{ color: '#5a6478', marginTop: 2 }}>{versionItem.desc}</div>}
            </>
          ) : (
            <div style={{ color: '#9ba3b2' }}>（无对应条目）</div>
          )}
        </div>
      </div>
    </div>
  )

  return (
    <div>
      {/* Toolbar */}
      <div style={{
        background: '#fff', border: '1px solid var(--color-border)', borderRadius: 10,
        padding: '12px 18px', marginBottom: 12, display: 'flex', alignItems: 'center',
        gap: 14, justifyContent: 'space-between', flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>报告周期</span>
          <button
            onClick={() => setPeriodSheetOpen(true)}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '5px 10px', border: '1px solid var(--color-border)',
              borderRadius: 6, fontSize: 12, fontFamily: 'inherit',
              background: '#f8fafc', cursor: 'pointer',
              color: 'var(--color-text-secondary)',
            }}
          >
            <Calendar size={14} />
            {reportPeriod}
          </button>
          <span style={{ color: 'var(--color-border)', fontSize: 15 }}>|</span>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>数据来源：近30天 AI 咨询记录</span>
        </div>
        {!isMobile && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className={`btn btn-sm${editing ? ' btn-primary' : ' btn-secondary'}`}
              onClick={() => setEditing((v) => !v)}
              style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
              {editing ? '退出编辑' : '编辑报告'}
            </button>
            <button className="btn btn-sm btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              导出 PDF
            </button>
          </div>
        )}
      </div>

      {/* Perspective tabs */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginBottom: 8 }}>策略视角</div>
        <div className="page-tabs" style={{ display: 'flex', gap: 2, background: '#f1f5f9', padding: 3, borderRadius: 10, width: 'fit-content' }}>
          {Object.entries(PERSPECTIVES).map(([k, v]) => (
            <button
              key={k}
              onClick={() => switchView(k)}
              style={{
                padding: '7px 20px', border: 'none', borderRadius: 8, cursor: 'pointer',
                fontSize: 12, fontWeight: view === k ? 600 : 400, fontFamily: 'inherit',
                background: view === k ? '#fff' : 'transparent',
                color: view === k ? 'var(--color-brand-800)' : 'var(--color-text-secondary)',
                boxShadow: view === k ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                transition: 'all 0.15s',
              }}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Three columns */}
      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', gap: isMobile ? 8 : 12, marginBottom: 12 }}>
        {/* Concerns */}
        <div style={{
          background: '#fff', border: '1px solid var(--color-border)', borderRadius: 10,
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '12px 14px', borderBottom: '1px solid var(--color-border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>学生高频关注</div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                按咨询频次排序 · 共 {data.concerns.length} 项{editing ? ' · 可拖拽排序' : ''}
              </div>
            </div>
            {editing && (
              <button onClick={() => addItem('concerns')} style={{
                fontSize: 10, padding: '3px 10px', border: '1px dashed var(--color-border)',
                background: 'transparent', borderRadius: 4, cursor: 'pointer',
                color: 'var(--color-text-secondary)', fontFamily: 'inherit',
              }}>
                + 添加
              </button>
            )}
          </div>
          <div style={{ padding: '6px 14px' }}>
            {data.concerns.map((c, i) => renderEditableCell('concerns', c, i, 'var(--color-brand-800)'))}
          </div>
        </div>

        {/* Gaps */}
        <div style={{
          background: '#fff', border: '1px solid var(--color-border)', borderRadius: 10,
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '12px 14px', borderBottom: '1px solid var(--color-border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>现有内容缺口</div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                按漏覆盖影响排序 · 共 {data.gaps.length} 项{editing ? ' · 可拖拽排序' : ''}
              </div>
            </div>
            {editing && (
              <button onClick={() => addItem('gaps')} style={{
                fontSize: 10, padding: '3px 10px', border: '1px dashed var(--color-border)',
                background: 'transparent', borderRadius: 4, cursor: 'pointer',
                color: 'var(--color-text-secondary)', fontFamily: 'inherit',
              }}>
                + 添加
              </button>
            )}
          </div>
          <div style={{ padding: '6px 14px' }}>
            {data.gaps.map((g, i) => renderEditableCell('gaps', g, i, 'var(--color-warning)'))}
          </div>
        </div>

        {/* Actions */}
        <div style={{
          background: '#fff', border: '1px solid var(--color-border)', borderRadius: 10,
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '12px 14px', borderBottom: '1px solid var(--color-border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>改进建议</div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                按优先级排列 · 共 {data.actions.length} 项 · 可编辑修改
              </div>
            </div>
            {editing && (
              <button onClick={() => addItem('actions')} style={{
                fontSize: 10, padding: '3px 10px', border: '1px dashed var(--color-border)',
                background: 'transparent', borderRadius: 4, cursor: 'pointer',
                color: 'var(--color-text-secondary)', fontFamily: 'inherit',
              }}>
                + 添加
              </button>
            )}
          </div>
          <div style={{ padding: '6px 14px' }}>
            {data.actions.map((a, i) => renderEditableCell('actions', a, i, 'var(--color-success)'))}
          </div>
        </div>
      </div>

      {/* Mobile sticky action bar */}
      {isMobile && (
        <div style={{
          position: 'sticky', bottom: 0, zIndex: 50,
          background: '#fff', border: '1px solid var(--color-border)',
          borderTopLeftRadius: 14, borderTopRightRadius: 14,
          padding: '10px 16px', display: 'flex', gap: 10,
          boxShadow: '0 -4px 16px rgba(15,23,42,0.08)',
          marginBottom: 12,
        }}>
          <button
            className={`btn${editing ? ' btn-primary' : ' btn-secondary'}`}
            onClick={() => setEditing((v) => !v)}
            style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 13, padding: '10px 0' }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            {editing ? '完成编辑' : '编辑报告'}
          </button>
          <button
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 13, padding: '10px 14px' }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            导出
          </button>
        </div>
      )}

      {/* Bottom bar */}
      <div style={{
        background: '#fff', border: '1px solid var(--color-border)', borderRadius: 10,
        padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: 8,
      }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>上次保存：5分钟前</span>
          <span style={{ color: 'var(--color-border)' }}>|</span>
          <button
            onClick={() => setShowHistory((v) => !v)}
            className="btn btn-sm btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            历史版本 ({versions.length})
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => { setData(structuredClone(systemVersion)); setEditing(false) }}
          >
            重置为系统建议
          </button>
          <button className="btn btn-sm btn-primary">保存报告</button>
        </div>
      </div>

      {/* Version History Panel */}
      {showHistory && (
        <div style={{
          marginTop: 12, background: '#fff', border: '1px solid var(--color-border)',
          borderRadius: 10, overflow: 'hidden', animation: 'page-enter 0.2s ease',
        }}>
          <div style={{
            padding: '10px 16px', background: '#f8fafc', borderBottom: '1px solid var(--color-border)',
            fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            报告历史版本
            <span style={{ fontSize: 10, color: 'var(--color-text-muted)', fontWeight: 400 }}>
              点击版本可查看该时间点的报告快照
            </span>
            <button
              onClick={() => { setShowHistory(false); setSelectedVersion(null) }}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#9ba3b2', fontSize: 16 }}
            >
              ×
            </button>
          </div>
          <div style={{ display: 'flex', maxHeight: isMobile ? undefined : 260, flexDirection: isMobile ? 'column' : 'row' }}>
            <div style={{
              width: isMobile ? '100%' : 200, borderRight: isMobile ? 'none' : '1px solid #f1f5f9',
              borderBottom: isMobile ? '1px solid #f1f5f9' : 'none',
              overflowY: 'auto', maxHeight: isMobile ? 200 : undefined,
              flexShrink: 0, padding: '4px 0',
            }}>
              <div onClick={() => setSelectedVersion(null)} style={{
                padding: '10px 14px', cursor: 'pointer',
                borderLeft: `3px solid ${selectedVersion === null ? 'var(--color-brand-800)' : 'transparent'}`,
                background: selectedVersion === null ? '#f8fafc' : 'transparent',
              }}>
                <div style={{ fontWeight: 600, fontSize: 12 }}>当前修改</div>
                <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>未保存的更改</div>
              </div>
              {versions.map((v, i) => (
                <div key={i} onClick={() => setSelectedVersion(i)} style={{
                  padding: '10px 14px', cursor: 'pointer',
                  borderLeft: `3px solid ${selectedVersion === i ? 'var(--color-brand-800)' : 'transparent'}`,
                  background: selectedVersion === i ? '#f8fafc' : 'transparent',
                }}>
                  <div style={{ fontSize: 12 }}>{v.label}</div>
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>{v.time}</div>
                </div>
              ))}
            </div>
            <div style={{ flex: 1, padding: 14, overflowY: 'auto' }}>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 12 }}>
                对比：当前修改 ← → {selectedVersion !== null ? versions[selectedVersion].label : '系统建议'}
              </div>
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 8, color: 'var(--color-brand-800)' }}>改进建议</div>
              {data.actions.map((a, i) => renderDiffCell(a, selectedData?.actions?.[i] || null))}
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 8, marginTop: 14, color: 'var(--color-brand-800)' }}>学生高频关注</div>
              {data.concerns.map((c, i) => renderDiffCell(c, selectedData?.concerns?.[i] || null))}
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 8, marginTop: 14, color: 'var(--color-brand-800)' }}>现有内容缺口</div>
              {data.gaps.map((g, i) => renderDiffCell(g, selectedData?.gaps?.[i] || null))}
            </div>
          </div>
          {selectedVersion !== null && (
            <div style={{
              padding: '8px 16px', borderTop: '1px solid #f1f5f9',
              display: 'flex', gap: 8, justifyContent: 'flex-end', background: '#fafafa',
            }}>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => { setData(structuredClone(versions[selectedVersion].data)) }}
              >
                还原到此版本
              </button>
            </div>
          )}
        </div>
      )}

      <BottomSheet
        open={periodSheetOpen}
        title="报告周期"
        onClose={() => setPeriodSheetOpen(false)}
      >
        {['2026年5月', '2026年4月', '2026年3月'].map((opt) => {
          const isActive = reportPeriod === opt
          return (
            <button
              key={opt}
              className="bs-row"
              onClick={() => { setReportPeriod(opt); setPeriodSheetOpen(false) }}
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
