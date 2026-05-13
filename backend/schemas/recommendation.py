from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    recommendations: list[dict]
    profile_snapshot: dict
