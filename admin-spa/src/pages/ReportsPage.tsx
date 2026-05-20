import { useState } from 'react'

const REPORT_DATA: Record<string, {
  concerns: { q: string; count: number; action: string }[]
  gaps: { q: string; count: number; action: string }[]
  actions: { action: string; priority: string; impact: string }[]
}> = {
  '综合视角': {
    concerns: [
      { q: '计算机类专业就业是否饱和？', count: 847, action: '加强计算机学院就业数据展示，制作"毕业生去向图谱"专题页' },
      { q: '师范类vs非师范类有什么区别？', count: 691, action: '制作清晰的"师范/非师范专业对比"信息图，加入宣讲PPT' },
      { q: '这个专业毕业后平均薪资？', count: 568, action: '整理近三年各专业薪资数据，在咨询中主动提供' },
      { q: '你们学校和XX大学比哪个好？', count: 432, action: '准备竞品对比材料，突出本校差异化优势' },
      { q: '保研率到底怎么样？', count: 387, action: '公开近三年保研数据，按专业拆分，做成可视化图表' },
    ],
    gaps: [
      { q: '是否有企业合作/实习机会？', count: 412, action: '建立"校企合作"专题页，列出合作企业和实习基地' },
      { q: '转专业具体细则是什么？', count: 378, action: '在知识库中补充转专业政策文档，标注各专业转入条件' },
      { q: '校园周边交通和生活配套？', count: 312, action: '制作校园生活导览页，标注地铁/商圈/医院等配套' },
      { q: '有没有国际交流/交换项目？', count: 278, action: '整理国际交流项目清单，按国家和地区分类展示' },
      { q: '实验室/科研平台有哪些？', count: 245, action: '制作科研平台介绍专题，含实验室照片和导师研究方向' },
    ],
    actions: [
      { action: '优先补充"校企合作"和"转专业政策"知识条目', priority: 'P0', impact: '高' },
      { action: '在招生宣讲PPT中加入"毕业生去向图谱"和"专业薪资对比"', priority: 'P0', impact: '高' },
      { action: '开设6月线上专题直播：热门专业深度解读系列', priority: 'P1', impact: '中' },
      { action: '优化Chatbot主动推荐规则：当学生问到对比类问题时主动提供差异化信息', priority: 'P1', impact: '中' },
      { action: '建立竞品院校监测机制，每月更新竞品数据', priority: 'P2', impact: '中' },
    ],
  },
}

export default function ReportsPage() {
  const [perspective, setPerspective] = useState('综合视角')
  const data = REPORT_DATA[perspective] || REPORT_DATA['综合视角']

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 24 }}>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>报告周期</span>
        <select style={{ padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', background: 'var(--surface)' }}>
          <option>2026年5月</option><option>2026年4月</option><option>2026年3月</option>
        </select>
        <span style={{ fontSize: 12, color: 'var(--muted)', marginLeft: 12 }}>策略视角</span>
        <select value={perspective} onChange={(e) => setPerspective(e.target.value)} style={{ padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', background: 'var(--surface)' }}>
          <option>综合视角</option><option>专业吸引力视角</option><option>地域竞争力视角</option>
        </select>
      </div>

      {/* Tier 1: Student Concerns */}
      <div className="report-tier" style={{ borderLeftColor: 'var(--accent)' }}>
        <h4>第一层：学生关注变化</h4>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>基于近30天咨询数据，以下话题询问量最高，反映当前学生关注焦点</p>
        {data.concerns.map((c, i) => (
          <div key={i}>
            <div className="report-item">
              <span>{i + 1}. {c.q}</span>
              <span className="count">{c.count} 次</span>
            </div>
            <div className="report-action">→ {c.action}</div>
          </div>
        ))}
      </div>

      {/* Tier 2: Knowledge Gaps */}
      <div className="report-tier" style={{ borderLeftColor: 'var(--amber)' }}>
        <h4>第二层：现有宣讲缺口</h4>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>学生在咨询中频繁提及但知识库未覆盖或回答不充分的话题</p>
        {data.gaps.map((g, i) => (
          <div key={i}>
            <div className="report-item">
              <span>{i + 1}. {g.q}</span>
              <span className="count">{g.count} 次</span>
            </div>
            <div className="report-action">→ {g.action}</div>
          </div>
        ))}
      </div>

      {/* Tier 3: Recommended Actions */}
      <div className="report-tier" style={{ borderLeftColor: 'var(--green)' }}>
        <h4>第三层：建议招生动作</h4>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>基于以上分析，按优先级排列的招生优化建议</p>
        {data.actions.map((a, i) => (
          <div className="report-item" key={i}>
            <span>{i + 1}. {a.action}</span>
            <span style={{
              fontSize: 11, padding: '2px 8px', borderRadius: 100,
              background: a.priority === 'P0' ? 'oklch(94% 0.04 25)' : a.priority === 'P1' ? 'oklch(94% 0.04 85)' : 'oklch(94% 0.005 250)',
              color: a.priority === 'P0' ? 'var(--red)' : a.priority === 'P1' ? 'oklch(48% 0.12 85)' : 'var(--muted)',
            }}>
              {a.priority} · {a.impact}影响
            </span>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
        <button className="btn btn-primary btn-sm">导出 PDF 报告</button>
        <button className="btn btn-secondary btn-sm">发送至招生办邮箱</button>
      </div>
    </div>
  )
}
