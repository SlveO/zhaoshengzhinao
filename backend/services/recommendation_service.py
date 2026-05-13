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

RANKING_PROMPT = """你是高考志愿填报专家。下面是真实的候选院校数据，你必须从中选择排序，绝对不能编造或修改院校名和专业名。

## 学生画像
{profile}

## 候选院校列表（只能从这里选！）
{candidates}

## 严格规则
1. 从候选列表中选出 Top-10，按综合匹配度排序
2. college_name 和 major_name 必须与候选列表中完全一致，一个字都不能改
3. level 必须与候选列表一致
4. 标注冲刺/稳妥/保底：学生位次明显高于最低位次=保底，位次接近=稳妥，位次明显低于=冲刺
5. 每条推荐生成 2-3 条理由
6. 每条理由附带数据来源，source_url 使用候选列表中的来源链接

直接回复 JSON 数组（不要 markdown 标记）：
[
  {{
    "rank": 1,
    "college_name": "这里必须是候选列表中的真实院校名",
    "major_name": "这里必须是候选列表中的真实专业名",
    "level": "候选列表中的层次",
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
