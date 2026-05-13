export default function FilterBar({
  filters,
  onChange,
  count,
}: {
  filters: any
  onChange: (k: string, v: string) => void
  count: number
}) {
  return (
    <div className="flex gap-3 items-center flex-wrap">
      <span className="text-xs text-muted">筛选：</span>
      <select
        value={filters.level}
        onChange={(e) => onChange('level', e.target.value)}
        className="px-3 py-1.5 border border-border rounded-md text-xs bg-white"
      >
        <option value="">全部层次</option>
        <option value="985">985</option>
        <option value="211">211</option>
        <option value="双一流">双一流</option>
        <option value="省重点">省重点</option>
      </select>
      <select
        value={filters.city}
        onChange={(e) => onChange('city', e.target.value)}
        className="px-3 py-1.5 border border-border rounded-md text-xs bg-white"
      >
        <option value="">全部地区</option>
        <option>广州</option>
        <option>深圳</option>
        <option>珠海</option>
        <option>汕头</option>
        <option>东莞</option>
      </select>
      <span className="ml-auto text-xs text-muted">
        共 <strong>{count}</strong> 条推荐
      </span>
    </div>
  )
}
