import { Link } from 'react-router-dom'

export default function ProfileSummaryBar({ profile }: { profile: any }) {
  const items = [
    {
      icon: '\u{1F464}',
      label: '分数',
      value: profile?.score ? `${profile.score}` : '未设置',
    },
    {
      icon: '\u{1F52C}',
      label: '兴趣类型',
      value: profile?.riasec
        ? Object.entries(profile.riasec as Record<string, number>)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 1)
            .map(([k]) =>
              (
                {
                  R: '动手',
                  I: '研究',
                  A: '创造',
                  S: '助人',
                  E: '领导',
                  C: '规范',
                } as Record<string, string>
              )[k] || k,
            )
            .join('')
        : '未分析',
    },
    {
      icon: '\u{1F30D}',
      label: '地域偏好',
      value: profile?.region_pref?.length
        ? profile.region_pref.join(', ')
        : '未设置',
    },
  ]

  return (
    <div className="bg-white rounded-xl p-4 border border-border flex items-center gap-6 flex-wrap">
      {items.map((i) => (
        <div key={i.label} className="flex items-center gap-2">
          <span className="text-xl">{i.icon}</span>
          <div>
            <div className="text-xs text-muted">{i.label}</div>
            <div className="font-semibold text-text text-sm">{i.value}</div>
          </div>
        </div>
      ))}
      <Link
        to="/chat"
        className="ml-auto text-primary text-xs hover:underline"
      >
        修改画像 →
      </Link>
    </div>
  )
}
