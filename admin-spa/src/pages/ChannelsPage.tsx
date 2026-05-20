// TODO: replace with API GET /api/dashboard/channel-summary
const MOCK_CHANNELS = [
  { name: '官网', icon: '🌐', leads: 2350, conversionRate: '12.6%', change: '+3.2%', up: true, pct: 60 },
  { name: '微信公众号', icon: '💬', leads: 2189, conversionRate: '10.8%', change: '+1.5%', up: true, pct: 52 },
  { name: '微信小程序', icon: '📱', leads: 2015, conversionRate: '9.4%', change: '+0.8%', up: true, pct: 48 },
  { name: '线下宣讲会', icon: '🎤', leads: 2017, conversionRate: '8.9%', change: '-0.6%', up: false, pct: 46 },
]

export default function ChannelsPage() {
  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <select style={{
          padding: '6px 12px', border: '1px solid var(--color-border)',
          borderRadius: 8, fontSize: 13, fontFamily: 'inherit', background: '#fff',
        }}>
          <option>今天</option>
          <option>近7天</option>
          <option>近30天</option>
        </select>
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
    </div>
  )
}
