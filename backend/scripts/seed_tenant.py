"""Seed tenant scnu and admin user to Supabase."""
import asyncio
import hashlib
import json
import os
import uuid

DATABASE_URL = "postgresql://postgres.jbpjfwltcydyjecavbcy:zhaoshengzhinao2026@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"


def hash_password(password: str) -> str:
    salt = os.urandom(32).hex()
    return f"{salt}:{hashlib.sha256((salt + password).encode()).hexdigest()}"


async def seed():
    import asyncpg
    conn = await asyncpg.connect(DATABASE_URL)

    # Check if tenant exists
    t_id = await conn.fetchval("SELECT id FROM tenants WHERE slug = 'scnu'")
    if t_id:
        print(f"Tenant scnu already exists: {t_id}")
    else:
        t_id = uuid.uuid4()
        config = {
            "brand": {
                "name": "华南师范大学",
                "shortName": "华南师大",
                "primaryColor": "#1a3a6b",
                "secondaryColor": "#c41230",
                "welcomeText": "欢迎了解华南师范大学！",
            },
            "features": {
                "guestMode": True,
                "crossCollegeCompare": True,
            },
        }
        await conn.execute(
            "INSERT INTO tenants (id, name, slug, config, subscription_tier, status) "
            "VALUES ($1::uuid, $2, $3, $4::jsonb, 'basic', 'active')",
            t_id, "华南师范大学", "scnu", json.dumps(config),
        )
        print(f"Created tenant: scnu ({t_id})")

    # Check if user exists
    u_id = await conn.fetchval("SELECT id FROM users WHERE username = 'admin'")
    if u_id:
        print(f"User admin already exists: {u_id}")
    else:
        u_id = uuid.uuid4()
        pwd_hash = hash_password("admin123")
        await conn.execute(
            "INSERT INTO users (id, username, password_hash, region, score, subjects) "
            "VALUES ($1::uuid, $2, $3, '', 0, '')",
            u_id, "admin", pwd_hash,
        )
        print(f"Created user: admin ({u_id})")

    # Link user as admin of scnu tenant
    existing_link = await conn.fetchval(
        "SELECT id FROM tenant_users WHERE tenant_id = $1::uuid AND user_id = $2::uuid",
        t_id, u_id,
    )
    if existing_link:
        print(f"Tenant-user link already exists: {existing_link}")
    else:
        await conn.execute(
            "INSERT INTO tenant_users (id, tenant_id, user_id, role) "
            "VALUES ($1::uuid, $2::uuid, $3::uuid, 'admin')",
            uuid.uuid4(), t_id, u_id,
        )
        print(f"Linked admin user to scnu tenant as admin")

    await conn.close()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
