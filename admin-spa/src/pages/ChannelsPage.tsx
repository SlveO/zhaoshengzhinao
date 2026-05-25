import { useState } from 'react'
import { Calendar } from 'lucide-react'
import BottomSheet from '../components/BottomSheet'

// TODO: replace with API GET /api/dashboard/channel-summary
const MOCK_CHANNELS = [
  { name: '官网', icon: '🌐', leads: 2350, conversionRate: '12.6%', change: '+3.2%', up: true, pct: 60 },
  { name: '微信公众号', icon: '💬', leads: 2189, conversionRate: '10.8%', change: '+1.5%', up: true, pct: 52 },
  { name: '微信小程序', icon: '📱', leads: 2015, conversionRate: '9.4%', change: '+0.8%', up: true, pct: 48 },
  { name: '线下宣讲会', icon: '🎤', leads: 2017, conversionRate: '8.9%', change: '-0.6%', up: false, pct: 46 },
]

export default function ChannelsPage() {
  const [period, setPeriod] = useState('今天')
  const [periodSheetOpen, setPeriodSheetOpen] = useState(false)

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <button
          onClick={() => setPeriodSheetOpen(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '6px 12px', border: '1px solid var(--color-border)',
            borderRadius: 8, fontSize: 13, fontFamily: 'inherit',
            background: '#fff', cursor: 'pointer',
            color: 'var(--color-text-secondary)',
          }}
        >
          <Calendar size={14} />
          {period}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
        {MOCK_CHANNELS.map((ch) => (
          <div key={ch.name} className="card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>{ch.icon}</div>
            <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 4px' }}>{ch.name}</h3>
            <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--color-brand-800)', marginBottom: 4 }}>
              {ch.leads.toLocaleString()}
            </div>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 12 }}>
              今日新增线索
            </div>
            {/* Mini bar */}
            <div style={{
              height: 8, background: '#e5e9f2', borderRadius: 4, overflow: 'hidden',
              marginBottom: 8,
            }}>
              <div style={{
                height: '100%', width: `${ch.pct}%`,
                background: 'linear-gradient(90deg, var(--color-brand-300), var(--color-brand-800))',
                borderRadius: 4, transition: 'width 0.4s ease',
              }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
              <span style={{ color: ch.up ? 'var(--color-success)' : 'var(--color-danger)', fontWeight: 500 }}>
                转化率 {ch.conversionRate} {ch.up ? '↑' : '↓'}
              </span>
              <span style={{ color: 'var(--color-text-muted)' }}>vs 昨日 {ch.change}</span>
            </div>
          </div>
        ))}
      </div>

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
