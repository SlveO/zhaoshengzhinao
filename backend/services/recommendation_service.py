import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from config import settings
from knowledge_base.retriever import retrieve_candidates
from models.recommendation import Recommendation

llm = ChatOpenAI(
    model=settings.deepseek_model,
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
    temperature=0.3,
)

RANKING_PROMPT = """你是高考志愿填报专家。基于学生画像和候选院校数据，对以下候选进行精排并生成推荐理由。

## 学生画像
{profile}

## 候选院校列表
{candidates}

## 要求
1. 按综合匹配度排序，选出 Top-10
2. 每个推荐标注：冲刺/稳妥/保底（基于学生位次 vs 录取位次：学生位次明显低于录取位次=冲刺，接近=稳妥，明显高于=保底）
3. 每条推荐生成 2-3 条理由：分数匹配、兴趣匹配、就业前景
4. 每条理由附带数据来源引用

请直接回复 JSON 数组，不要包含 markdown 代码块标记：
[
  {{
    "rank": 1,
    "college_name": "大学名",
    "major_name": "专业名",
    "level": "985/211/双一流/省重点",
    "category": "冲刺/稳妥/保底",
    "match_score": 85,
    "reasons": [
      {{"type": "score_match", "content": "...", "source": "广东省教育考试院2024年录取数据", "source_url": "..."}},
      {{"type": "interest_match", "content": "...", "source": "霍兰德职业兴趣理论", "confidence": 0.88}}
    ],
    "scores": {{"admission_probability": 58, "interest_match": 92, "career_prospect": 85}}
  }}
]
"""


async def generate_recommendations(
    user_id: str, profile: dict, db: AsyncSession
) -> list[dict]:
    candidates = retrieve_candidates(profile, k=30)
    candidate_text = "\n".join(
        f"- {c['metadata']['college_name']} | {c['metadata']['major_name']} | {c['metadata']['level']} | 最低位次: {c['metadata']['min_rank']} | 最低分数: {c['metadata']['min_score']} | 选科: {c['metadata']['subjects']} | 来源: {c['metadata'].get('source_url', '')}"
        for c in candidates
    )
    profile_text = json.dumps(profile, ensure_ascii=False)
    prompt = RANKING_PROMPT.format(profile=profile_text, candidates=candidate_text)
    response = await llm.ainvoke(prompt)
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n```", 1)[0]
        recommendations = json.loads(content)
    except (json.JSONDecodeError, AttributeError):
        recommendations = []

    rec = Recommendation(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        profile_version=1,
        result_json=recommendations,
    )
    db.add(rec)
    await db.commit()
    return recommendations
