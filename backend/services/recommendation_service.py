import asyncio
import json
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import settings
from knowledge_base.retriever import retrieve_candidates
from models.recommendation import Recommendation

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.3,
            max_tokens=4096,
            timeout=120,
        )
    return _llm

RANKING_PROMPT = """你是高考志愿填报专家。下面是真实的候选院校数据，你必须从中选择排序，绝对不能编造或修改院校名和专业名。

## 学生画像
{profile}

## 候选院校列表（只能从这里选！）
{candidates}

## 行业就业数据参考
{industry_data}

## 严格规则
1. 从候选列表中选出 Top-10，按综合匹配度排序
2. college_name, major_name, level, city 必须与候选列表完全一致，一个字都不能改
3. 标注冲刺/稳妥/保底：学生位次明显高于最低位次=保底，位次接近=稳妥，位次明显低于=冲刺
4. 每条推荐生成 2-3 条理由
5. 每条理由附带数据来源，source_url 使用候选列表中的来源链接

直接回复 JSON 数组（不要 markdown 标记）：
[
  {{
    "rank": 1,
    "college_name": "这里必须是候选列表中的真实院校名",
    "major_name": "这里必须是候选列表中的真实专业名",
    "level": "候选列表中的层次",
    "city": "院校所在城市",
    "category": "冲刺/稳妥/保底",
    "match_score": 85,
    "reasons": [
      {{"type": "score_match", "content": "分数匹配说明...", "source": "广东省教育考试院2024年录取数据", "source_url": "候选列表中的来源URL"}},
      {{"type": "interest_match", "content": "兴趣匹配说明...", "source": "霍兰德职业兴趣理论", "confidence": 0.88}}
    ],
    "scores": {{"admission_probability": 58, "interest_match": 92, "career_prospect": 85}}
  }}
]
"""

L1_PROMPT_ADDON = """
## 匹配策略（基础推荐）
学生画像信息有限（仅分数+选科）。请主要依据位次匹配进行排序。
在理由中建议学生继续对话以获取更精准的推荐。
"""

L2_PROMPT_ADDON = """
## 匹配策略（较完整推荐）
学生画像包含：分数+选科+地域偏好+部分兴趣倾向。
权重分配：60% 位次匹配 + 25% 兴趣倾向 + 15% 地域偏好。
"""

L3_PROMPT_ADDON = """
## 匹配策略（深度个性化推荐）
学生画像包含：分数+选科+地域偏好+深度兴趣倾向+价值观排序。
权重分配：40% 位次匹配 + 35% 兴趣倾向 + 15% 价值观 + 10% 地域偏好。
"""


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((Exception,)),
    reraise=True,
)
async def _call_llm_with_retry(prompt: str):
    return await _get_llm().ainvoke(prompt)


def _get_adaptive_prompt(profile: dict) -> str:
    completeness = profile.get("completeness", "L1")
    if completeness == "L3":
        return RANKING_PROMPT + L3_PROMPT_ADDON
    elif completeness == "L2":
        return RANKING_PROMPT + L2_PROMPT_ADDON
    return RANKING_PROMPT + L1_PROMPT_ADDON


async def generate_recommendations(
    user_id: str, profile: dict, db: AsyncSession, tenant_slug: str | None = None
) -> list[dict]:
    candidates = retrieve_candidates(profile, k=30, tenant_slug=tenant_slug)

    # Enrich candidates with industry/career data
    from models.mapping import MajorIndustryMapping
    from models.industry import IndustryAnalysis
    major_names = list({c['metadata']['major_name'] for c in candidates})
    mapping_result = await db.execute(
        select(MajorIndustryMapping).where(
            MajorIndustryMapping.major_name.in_(major_names)
        )
    )
    major_map = {m.major_name: m for m in mapping_result.scalars().all()}

    ind_result = await db.execute(
        select(IndustryAnalysis).where(IndustryAnalysis.year == 2024)
    )
    industry_map = {i.industry_name: i for i in ind_result.scalars().all()}

    # Build enriched candidate text with industry data
    candidate_lines = []
    industry_summary = []
    seen_industries = set()
    for c in candidates:
        meta = c['metadata']
        major = meta['major_name']
        mapping = major_map.get(major)
        ind_info = ""
        if mapping and mapping.primary_industries:
            ind_names = ", ".join(mapping.primary_industries)
            ind_info = f" | 对口行业: {ind_names}"
            if mapping.salary_range:
                sr = mapping.salary_range
                ind_info += f" | 薪资范围: {sr.get('entry',0)}-{sr.get('senior',0)}元/月"
            # Collect industry summary
            for ind_name in mapping.primary_industries:
                if ind_name not in seen_industries:
                    seen_industries.add(ind_name)
                    ind = industry_map.get(ind_name)
                    if ind:
                        industry_summary.append(
                            f"- {ind_name}: 年均薪{ind.avg_annual_salary or 0:,.0f}元, "
                            f"需求指数{ind.employment_demand_index or 0}/5, "
                            f"入行难度{ind.entry_difficulty}, {ind.outlook}"
                        )

        candidate_lines.append(
            f"- {meta['college_name']} | {meta['major_name']} | "
            f"{meta['level']} | {meta.get('city', '')} | "
            f"最低位次: {meta['min_rank']} | 最低分数: {meta['min_score']} | "
            f"选科: {meta['subjects']} | 省份: {meta.get('province', '')}"
            f"{ind_info} | 来源: {meta.get('source_url', '')}"
        )
    candidate_text = "\n".join(candidate_lines)
    industry_text = "\n".join(industry_summary[:10]) if industry_summary else "暂无行业数据"

    # Query user feedback history for ranking hints
    from models.recommendation_feedback import RecommendationFeedback
    feedback_result = await db.execute(
        select(RecommendationFeedback).where(
            RecommendationFeedback.user_id == uuid.UUID(user_id)
        ).order_by(RecommendationFeedback.created_at.desc()).limit(20)
    )
    feedbacks = feedback_result.scalars().all()

    feedback_text = ""
    if feedbacks:
        liked = [f for f in feedbacks if f.feedback_type == "useful"]
        disliked = [f for f in feedbacks if f.feedback_type == "not_relevant"]
        if liked:
            feedback_text += f"- 之前标记为有用：{', '.join(f'{f.major_name}({f.college_name})' for f in liked[:5])}\n"
        if disliked:
            feedback_text += f"- 之前标记为不相关：{', '.join(f'{f.major_name}({f.college_name})' for f in disliked[:5])}\n"
        if feedback_text:
            feedback_text = "## 学生历史反馈\n" + feedback_text + "请参考此反馈，提升与\"有用\"类型相似的结果排序，降低与\"不相关\"类型相似的结果。\n"

    profile_text = json.dumps(profile, ensure_ascii=False)
    prompt_template = _get_adaptive_prompt(profile)
    prompt = prompt_template.format(
        profile=profile_text,
        candidates=candidate_text,
        industry_data=industry_text,
    )
    if feedback_text:
        prompt = prompt.replace("## 要求", feedback_text + "## 要求")

    # LLM call with retry + timeout
    try:
        response = await asyncio.wait_for(
            _call_llm_with_retry(prompt),
            timeout=90,
        )
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n```", 1)[0]
        recommendations = json.loads(content)
    except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
        recommendations = []
        print(f"Recommendation generation failed or timed out for user {user_id}")

    rec = Recommendation(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        profile_version=1,
        result_json=recommendations,
    )
    db.add(rec)
    await db.commit()

    # Write analytics event
    try:
        from core.event_writer import write_event
        await write_event(
            tenant_id=rec.tenant_id if hasattr(rec, 'tenant_id') and rec.tenant_id else None,
            event_type="recommendation.generated",
            user_id=uuid.UUID(user_id),
            payload={
                "profile_level": profile.get("completeness", "L1"),
                "candidates_count": len(candidates),
                "output_count": len(recommendations),
            },
        )
    except Exception:
        pass  # Event writing failure should not block the recommendation

    return recommendations
