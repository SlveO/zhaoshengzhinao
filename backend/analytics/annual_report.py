"""Annual report — aggregate all analytics modules into a structured report."""
from datetime import datetime, timezone, timedelta

from analytics.funnel import get_funnel
from analytics.profile_dashboard import get_profile_dashboard
from analytics.major_heatmap import get_major_heatmap
from analytics.region_distribution import get_region_distribution
from analytics.competitive_analysis import get_competitive_analysis


async def get_annual_report(tenant_id: str, days: int = 365) -> dict:
    funnel = await get_funnel(tenant_id, days=days)
    dashboard = await get_profile_dashboard(tenant_id, days=days)
    heatmap = await get_major_heatmap(tenant_id, days=days)
    regions = await get_region_distribution(tenant_id, days=days)
    competitive = await get_competitive_analysis(tenant_id, days=days)

    year = datetime.now(timezone.utc).year

    sections = []

    sections.append({
        "title": "招生漏斗概览",
        "content": (
            f"本周期内共有 {funnel['stages']['visitors']} 名访客，"
            f"其中 {funnel['stages']['conversations']} 次对话 session，"
            f"{funnel['stages']['deepConsultations']} 次深度画像建档，"
            f"{funnel['stages']['intentExpressed']} 名意向表达。"
            f"访客到对话转化率 {funnel['conversionRates']['visitorToConversation']}%。"
        ),
        "charts": ["funnel_chart"],
    })

    top_majors = heatmap.get("majors", [])[:5]
    sections.append({
        "title": "热门专业分析",
        "content": (
            f"热度最高的专业：{', '.join(m['majorName'] for m in top_majors) if top_majors else '暂无数据'}。"
            f"共覆盖 {len(heatmap.get('majors', []))} 个专业方向。"
        ),
        "charts": ["major_heatmap_chart"],
    })

    section_scores = {}
    for d in dashboard.get("riasecDistribution", []):
        section_scores[d["dimension"]] = d["avgScore"]
    top_dims = sorted(section_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    sections.append({
        "title": "学生画像特征",
        "content": (
            f"学生群体最突出的能力维度：{', '.join(f'{dim}({score})' for dim, score in top_dims)}。"
            f"累计画像数量 {dashboard.get('totalProfiles', 0)}。"
        ),
        "charts": ["riasec_radar_chart"],
    })

    top_regions = regions.get("regions", [])[:3]
    sections.append({
        "title": "生源地域分布",
        "content": (
            f"生源最多的省份：{', '.join(r['province'] for r in top_regions) if top_regions else '暂无数据'}。"
            f"覆盖 {len(regions.get('regions', []))} 个省份。"
        ),
        "charts": ["region_map_chart"],
    })

    loss_items = competitive.get("lossAnalysis", [])
    loss_text = "；".join(f"{item['reason']}（{item['percentage']}%）" for item in loss_items[:3])
    sections.append({
        "title": "竞争与流失分析",
        "content": f"主要流失原因：{loss_text if loss_text else '暂无数据'}。",
        "charts": ["loss_pie_chart"],
    })

    summary = (
        f"{year}年度招生分析报告："
        f"累计服务 {funnel['stages']['visitors']} 名潜在学生，"
        f"完成 {dashboard.get('totalProfiles', 0)} 份学生画像，"
        f"覆盖 {len(heatmap.get('majors', []))} 个专业方向和 {len(regions.get('regions', []))} 个省份。"
    )

    return {
        "report": {
            "year": year,
            "summary": summary,
            "sections": sections,
        },
    }
