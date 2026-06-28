import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from tenants.models import TenantUser
from utils.security import hash_password, verify_password
from utils.jwt import create_token
from config import settings


async def register_user(db: AsyncSession, username: str, password: str, region: str, score: int, subjects: str, rank: int | None = None) -> User | None:
    """学生注册(mini-app 端)。仅写入 users 表,不创建 tenant_users 关联。"""
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        return None
    user = User(id=uuid.uuid4(), username=username, password_hash=hash_password(password), region=region, score=score, subjects=subjects, rank=rank)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> dict | None:
    """验证用户名密码,并从 tenant_users.role 推导 is_developer 标记。

    登录流程:
    1. 查 users 表验证密码
    2. left join tenant_users 取 role
    3. is_developer = (role == 'developer')
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None

    # 查 tenant_users 取 role(学生无记录 → role=None)
    result = await db.execute(
        select(TenantUser).where(TenantUser.user_id == user.id)
    )
    tenant_user = result.scalar_one_or_none()
    role = tenant_user.role if tenant_user else None
    is_developer = role == "developer" or username == settings.dev_admin_username

    return {
        "user_id": str(user.id),
        "username": user.username,
        "is_developer": is_developer,
        "role": role,
    }


def generate_tokens(user_id: str, username: str, is_developer: bool = False, role: str | None = None) -> dict:
    """生成 JWT。同时包含 is_developer(向后兼容)和 role(新标准)。"""
    return {
        "access_token": create_token(
            user_id, username, settings.access_token_expire_minutes,
            extra_claims={"is_developer": is_developer, "role": role},
        ),
        "refresh_token": create_token(
            user_id, username, settings.refresh_token_expire_days * 24 * 60,
            extra_claims={"is_developer": is_developer, "role": role},
        ),
    }
