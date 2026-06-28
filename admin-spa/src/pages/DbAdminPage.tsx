import { useState } from 'react'
import TablesTab from '../components/db/TablesTab'
import KnowledgeRawTab from '../components/db/KnowledgeRawTab'
import SchemaTab from '../components/db/SchemaTab'

type TabKey = 'tables' | 'knowledge' | 'schema'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'tables', label: '数据表管理' },
  { key: 'knowledge', label: '知识库 Raw' },
  { key: 'schema', label: '表结构' },
]

export default function DbAdminPage() {
  const [tab, setTab] = useState<TabKey>('tables')

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 16 }}>数据库管理</h1>
      <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid var(--color-border, #e5e7eb)', marginBottom: 16 }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: '8px 16px',
              border: 'none',
              background: tab === t.key ? 'var(--color-primary, #1a3a6b)' : 'transparent',
              color: tab === t.key ? '#fff' : 'inherit',
              cursor: 'pointer',
              borderBottom: tab === t.key ? '2px solid var(--color-primary, #1a3a6b)' : '2px solid transparent',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'tables' && <TablesTab />}
      {tab === 'knowledge' && <KnowledgeRawTab />}
      {tab === 'schema' && <SchemaTab />}
    </div>
  )
}
