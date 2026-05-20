import { useState } from 'react'

// TODO: replace with API GET /api/strategy/report?view=
const REPORT_DATA: Record<string, {
  concerns: { rank: number; title: string; desc: string; blurred?: boolean }[]
  gaps: { rank: number; title: string; desc: string; blurred?: boolean }[]
  actions: { rank: number; title: string; desc: string; blurred?: boolean }[]
  moreCount: number
}> = {
  'weekly': {
    concerns: [
      { rank: 1, title: '就业去向咨询上升', desc: '电子信息类、计算机方向的就业去向持续被追问。' },
      { rank: 2, title: '转专业政策被反复追问', desc: '学生希望知道入校后的调整空间和具体规则。' },
      { rank: 3, title: '电子信息类专业热度提升', desc: '' },
      { rank: 4, title: '家长更关注就读条件', desc: '宿舍、食堂、校园安全等问题明显多于往年。', blurred: true },
    ],
    gaps: [
      { rank: 1, title: '电子信息类就业案例不足', desc: '现有材料对就业去向、企业类型和岗位说明不够具体。' },
      { rank: 2, title: '转专业政策解释不够直观', desc: '规则入口分散，学生难以快速理解申请条件与流程。' },
      { rank: 3, title: '近三年录取位次入口不明显', desc: '' },
      { rank: 4, title: '专业培养方案缺乏学生化表达', desc: '表述偏行政化，学生和家长理解门槛较高。', blurred: true },
    ],
    actions: [
      { rank: 1, title: '发布《电子信息类专业就业去向解析》推文', desc: '用真实去向、企业类型和岗位方向回应就业顾虑。' },
      { rank: 2, title: '在公众号菜单新增"转专业政策说明"', desc: '把申请条件、时间节点和问题集中呈现。' },
      { rank: 3, title: '宣讲会增加"近三年录取位次解读"环节', desc: '' },
      { rank: 4, title: '定向广告物料补充专业培养与就业信息', desc: '针对电子信息、计算机等热门专业制作专题页。', blurred: true },
    ],
    moreCount: 2,
  },
  'content': {
    concerns: [
      { rank: 1, title: '学生对专业课程内容了解不足', desc: '多数学生对"电子信息工程学什么"缺乏基本认知。' },
      { rank: 2, title: '培养方案关键信息缺失', desc: '学生关心辅修、双学位等个性化培养路径。' },
      { rank: 3, title: '师资介绍吸引力不够', desc: '' },
      { rank: 4, title: '国际化学习机会少', desc: '海外交换、联合培养等信息不充分。', blurred: true },
    ],
    gaps: [
      { rank: 1, title: '缺少"专业课程地图"可视化', desc: '学生想了解四年学习路径，但现有材料以文字为主。' },
      { rank: 2, title: '优秀毕业生案例未充分利用', desc: '校友故事分散在新闻中，未作为招生材料集中展示。' },
      { rank: 3, title: '实验室/科研平台介绍缺乏吸引力', desc: '' },
      { rank: 4, title: '校园文化内容不够生动', desc: '', blurred: true },
    ],
    actions: [
      { rank: 1, title: '制作交互式"专业课程地图"H5', desc: '把四年课程、实践、实习路径可视化呈现。' },
      { rank: 2, title: '整理"校友故事集"专题页', desc: '按专业分类，突出就业和升学成果。' },
      { rank: 3, title: '为每个重点实验室拍摄短视频导览', desc: '' },
      { rank: 4, title: '开发校园 VR 导览', desc: '', blurred: true },
    ],
    moreCount: 3,
  },
  'lecture': {
    concerns: [
      { rank: 1, title: '宣讲会内容与线上咨询差异大', desc: '学生在宣讲会上听到的信息与线上咨询不一致。' },
      { rank: 2, title: '家长关注点与预设内容错位', desc: '家长更关心就业和费用，但宣讲以学术介绍为主。' },
      { rank: 3, title: '针对性不足', desc: '' },
      { rank: 4, title: '时间安排不够灵活', desc: '', blurred: true },
    ],
    gaps: [
      { rank: 1, title: '宣讲缺少问答环节数据分析', desc: '宣讲后的集体问答未系统化为知识库补充。' },
      { rank: 2, title: '不同省份的差异化宣讲策略缺失', desc: '各省份关注点差异大，但宣讲内容统一。' },
      { rank: 3, title: '线下咨询效率偏低', desc: '' },
      { rank: 4, title: '缺乏后续跟进的系统流程', desc: '', blurred: true },
    ],
    actions: [
      { rank: 1, title: '建立宣讲效果反馈闭环', desc: '每次宣讲后自动分析问答数据，更新宣讲重点。' },
      { rank: 2, title: '按省份定制宣讲内容', desc: '基于本省学生咨询数据调整宣讲侧重点。' },
      { rank: 3, title: '增设家长专场', desc: '' },
      { rank: 4, title: '开发面向家长的决策辅助工具', desc: '', blurred: true },
    ],
    moreCount: 2,
  },
}

const PERSPECTIVES: Record<string, string> = {
  'weekly': '综合视角',
  'content': '内容优化',
  'lecture': '宣讲重点',
}

export default function ReportsPage() {
  const [view, setView] = useState('weekly')
  const data = REPORT_DATA[view]

  return (
    <div>
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <span className="pill pill-blue" style={{ marginBottom: 12, display: 'inline-block', fontSize: 11 }}>
          招生策略反哺
        </span>
        <h2 style={{
          fontSize: 26, fontWeight: 900, margin: '12px 0 6px',
          letterSpacing: '-0.03em', lineHeight: 1.3,
        }}>
          让真实咨询数据，
          <br />
          指导下一次招生动作
        </h2>
        <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', maxWidth: 520, margin: '0 auto' }}>
          系统自动分析学生咨询数据，识别招生策略中的具体优化点，
          从"学生问什么"到"学校该做什么"，形成完整的策略反哺闭环。
        </p>
      </div>

      {/* Perspective Tabs */}
      <div style={{
        display: 'flex', gap: 6, justifyContent: 'center', marginBottom: 22,
        background: '#f1f5f9', padding: 4, borderRadius: 10, width: 'fit-content', margin: '0 auto 22px',
      }}>
        {Object.entries(PERSPECTIVES).map(([k, v]) => (
          <button
            key={k}
            onClick={() => setView(k)}
            style={{
              padding: '6px 18px', borderRadius: 8, border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: view === k ? 600 : 400, fontFamily: 'inherit',
              background: view === k ? '#fff' : 'transparent',
              color: view === k ? 'var(--color-brand-800)' : 'var(--color-text-secondary)',
              boxShadow: view === k ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
              transition: 'all 0.15s',
            }}
          >
            {v}
          </button>
        ))}
      </div>

      {/* Report header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 18, fontSize: 13,
      }}>
        <div>
          <span style={{ fontWeight: 600, fontSize: 15 }}>招生策略报告</span>
          <span style={{ color: 'var(--color-brand-800)', marginLeft: 8, fontSize: 12, fontWeight: 500 }}>
            从数据洞察，到招生动作
          </span>
        </div>
        <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>
          当前视角：{PERSPECTIVES[view]} · 学生问了什么 → 学校哪里没讲清楚 → 下一步该怎么做
        </div>
      </div>

      {/* Three columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 20 }}>
        {/* Concerns */}
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>学生关注变化</h3>
          <p style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 0, marginBottom: 14 }}>
            近30天咨询中追问频次最高的话题
          </p>
          {data.concerns.map((c) => (
            <div key={c.rank} className={c.blurred ? 'blurred-row' : ''} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'start' }}>
                <span style={{
                  width: 22, height: 22, borderRadius: '50%', background: 'var(--color-brand-800)',
                  color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 600, flexShrink: 0,
                }}>
                  {c.rank}
                </span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{c.title}</div>
                  {c.desc && <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>{c.desc}</div>}
                </div>
              </div>
            </div>
          ))}
          <div style={{ fontSize: 12, color: 'var(--color-brand-800)', fontWeight: 500, cursor: 'pointer' }}>
            还有 {data.moreCount} 条...
          </div>
        </div>

        {/* Gaps */}
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>现有宣讲缺口</h3>
          <p style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 0, marginBottom: 14 }}>
            当前知识库未能充分覆盖的高频问题
          </p>
          {data.gaps.map((g) => (
            <div key={g.rank} className={g.blurred ? 'blurred-row' : ''} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'start' }}>
                <span style={{
                  width: 22, height: 22, borderRadius: '50%', background: 'var(--color-warning)',
                  color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 600, flexShrink: 0,
                }}>
                  {g.rank}
                </span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{g.title}</div>
                  {g.desc && <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>{g.desc}</div>}
                </div>
              </div>
            </div>
          ))}
          <div style={{ fontSize: 12, color: 'var(--color-brand-800)', fontWeight: 500, cursor: 'pointer' }}>
            还有 {data.moreCount} 条...
          </div>
        </div>

        {/* Actions */}
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>建议招生动作</h3>
          <p style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 0, marginBottom: 14 }}>
            按优先级排列的招生优化建议
          </p>
          {data.actions.map((a) => (
            <div key={a.rank} className={a.blurred ? 'blurred-row' : ''} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'start' }}>
                <span style={{
                  width: 22, height: 22, borderRadius: '50%', background: 'var(--color-success)',
                  color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 600, flexShrink: 0,
                }}>
                  {a.rank}
                </span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{a.title}</div>
                  {a.desc && <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>{a.desc}</div>}
                </div>
              </div>
            </div>
          ))}
          <div style={{ fontSize: 12, color: 'var(--color-brand-800)', fontWeight: 500, cursor: 'pointer' }}>
            还有 {data.moreCount} 条...
          </div>
        </div>
      </div>

      {/* Bottom CTA */}
      <p style={{
        textAlign: 'center', fontSize: 13, color: 'var(--color-text-muted)',
        paddingTop: 8, borderTop: '1px solid var(--color-border)',
      }}>
        每一次咨询反馈，都会成为下一轮招生优化的依据。
      </p>
    </div>
  )
}
