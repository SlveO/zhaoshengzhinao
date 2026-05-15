from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gaokao:gaokao@db:5432/gaokao"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours — avoid kicking users during demo
    refresh_token_expire_days: int = 7
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-v4-flash"
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    chroma_persist_dir: str = "./chroma_data"

    class Config:
        env_file = ".env"


settings = Settings()
