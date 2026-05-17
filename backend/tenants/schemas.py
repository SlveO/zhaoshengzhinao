from pydantic import BaseModel


class BrandConfig(BaseModel):
    name: str = ""
    short_name: str = ""
    primary_color: str = "#2563eb"
    secondary_color: str = "#f59e0b"
    logo_url: str = ""
    welcome_text: str = ""


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    subscription_tier: str
    status: str

    class Config:
        from_attributes = True


class TenantConfigUpdate(BaseModel):
    brand: BrandConfig | None = None
