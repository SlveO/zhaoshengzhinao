import { useState } from 'react'

// TODO: replace with API GET /api/leads?intent=high&sort=score
const MOCK_LEADS = [
  { id: 'A001', name: '学生A', intentScore: 92, province: '广东', subjectType: '物理类', score: 585, major: '电子信息方向', concerns: ['就业去向', '转专业', '录取位次'], action: 'priority' as const },
  { id: 'A002', name: '学生B', intentScore: 85, province: '湖南', subjectType: '历史类', score: 562, major: '师范方向', concerns: ['保研率', '课程设置'], action: 'suggest' as const },
  { id: 'A003', name: '学生C', intentScore: 71, province: '广西', subjectType: '物理类', score: 528, major: '数据科学方向', concerns: ['实验室条件'], action: 'observe' as const },
  { id: 'A004', name: '学生D', intentScore: 88, province: '江西', subjectType: '物理类', score: 602, major: '计算机科学', concerns: ['就业率', '薪资水平', '校企合作'], action: 'priority' as const },
  { id: 'A005', name: '学生E', intentScore: 79, province: '福建', subjectType: '历史类', score: 548, major: '法学方向', concerns: ['司法考试通过率'], action: 'suggest' as const },
]

// TODO: replace with API GET /api/leads/:id/detail
const MOCK_DETAIL = {
  suggestion: {
    urgency: '24小时内人工跟进',
    reason: '该学生多次追问就业与录取可能性，已经进入高意向跟进区。',
    profile: '广东 / 物理类 / 585分 / 电子信息方向',
    coreInterests: '就业去向、转专业政策、近三年录取位次',
    suggestedAction: '建议招生老师 24 小时内人工跟进。',
    materials: '电子信息类就业案例、专业培养方案、近三年录取位次说明。',
  },
}

const ACTION_MAP: Record<string, { label: string; className: string; style?: React.CSSProperties }> = {
  priority: { label: '优先跟进', className: 'btn btn-primary btn-sm' },
  suggest: { label: '建议联系', className: 'btn btn-sm', style: { color: 'var(--color-brand-800)', background: 'transparent', fontWeight: 500 } },
  observe: { label: '持续观察', className: 'btn btn-sm', style: { color: 'var(--color-text-muted)' } },
}

export default function LeadWorkbenchPage() {
  const [selected, setSelected] = useState<string | null>(null)
  const selectedLead = MOCK_LEADS.find((l) => l.id === selected)

  return (
    <div>
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', letterSpacing: '0.06em', marginBottom: 2 }}>
                LEAD WORKBENCH
              </div>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>
                高意向生源工作台
              </h2>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>今日新增</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--color-brand-800)' }}>
                18<span style={{ fontSize: 13, color: 'var(--color-text-secondary)', fontWeight: 400 }}> 条高意向线索</span>
              </div>
            </div>
          </div>

          {/* Pipeline Steps */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>
            {['咨询沉淀', '标签提取', '意向评分', '人工跟进'].map((step, i) => (
              <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  padding: '4px 14px', borderRadius: 20, fontWeight: i === 3 ? 600 : 400,
                  background: i === 3 ? 'var(--color-brand-800)' : '#f1f5f9',
                  color: i === 3 ? '#fff' : 'var(--color-text-secondary)',
                }}>
                  {step}
                </span>
                {i < 3 && <span style={{ color: 'var(--color-text-muted)' }}>→</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ width: '25%' }}>线索</th>
                <th>画像与关注点</th>
                <th style={{ width: 120, textAlign: 'right' }}>动作</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_LEADS.map((lead) => (
                <tr
                  key={lead.id}
                  className={selected === lead.id ? 'selected' : ''}
                  style={{ cursor: 'pointer', borderLeft: selected === lead.id ? '3px solid var(--color-brand-800)' : '3px solid transparent' }}
                  onClick={() => setSelected(selected === lead.id ? null : lead.id)}
                >
                  <td>
                    <span style={{ fontWeight: 600 }}>{lead.name}</span>
                    <span className="pill pill-blue" style={{ marginLeft: 8 }}>
                      意向 {lead.intentScore}
                    </span>
                  </td>
                  <td>
                    <div style={{ fontWeight: 500 }}>
                      {lead.province} / {lead.subjectType} / {lead.score}分
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '2px 0' }}>
                      {lead.major}
                    </div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {lead.concerns.map((c) => (
                        <span key={c} style={{
                          fontSize: 10, background: '#f1f5f9', padding: '1px 6px',
                          borderRadius: 3, color: 'var(--color-text-secondary)',
                        }}>
                          {c}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button {...ACTION_MAP[lead.action]}>{ACTION_MAP[lead.action].label}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Panel */}
      {selectedLead && (
        <div className="card" style={{ marginTop: 12, animation: 'page-enter 0.2s ease' }}>
          <div style={{ display: 'flex', gap: 20 }}>
            <div style={{ flex: 1.2 }}>
              <span style={{ fontSize: 11, color: 'var(--color-brand-800)', fontWeight: 500 }}>
                当前线索建议
              </span>
              <div style={{ fontSize: 18, fontWeight: 700, margin: '4px 0' }}>
                {MOCK_DETAIL.suggestion.urgency}
              </div>
              <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.6, margin: 0 }}>
                {MOCK_DETAIL.suggestion.reason}
              </p>
            </div>
            <div style={{ flex: 0.8, borderLeft: '1px solid var(--color-border)', paddingLeft: 18 }}>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 4 }}>学生画像</div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{MOCK_DETAIL.suggestion.profile}</div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 10, marginBottom: 4 }}>核心关注</div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{MOCK_DETAIL.suggestion.coreInterests}</div>
            </div>
            <div style={{ flex: 0.8, borderLeft: '1px solid var(--color-border)', paddingLeft: 18 }}>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 4 }}>建议动作</div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', marginBottom: 10 }}>{MOCK_DETAIL.suggestion.suggestedAction}</div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 4 }}>推荐材料</div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{MOCK_DETAIL.suggestion.materials}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
