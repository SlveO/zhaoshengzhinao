from pydantic import BaseModel, Field

class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    region: str = ""
    score: int = 0
    subjects: str = ""
    rank: int | None = None

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    username: str
    is_developer: bool = False
    role: str | None = None
