"""Ensure scnu college admin account exists in cloud Supabase.

Creates/updates:
  - User 'scnu' with password 'scnu2026' (idempotent, updates password if exists)
  - TenantUser link scnu -> scnu tenant with role='admin'
"""
import asyncio
import hashlib
import os
import uuid

DATABASE_URL = "postgresql://postgres.jbpjfwltcydyjecavbcy:zhaoshengzhinao2026@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"


def hash_password(password: str) -> str:
    salt = os.urandom(32).hex()
    return f"{salt}:{hashlib.sha256((salt + password).encode()).hexdigest()}"


async def main():
    import asyncpg
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Find scnu tenant
        t_id = await conn.fetchval("SELECT id FROM tenants WHERE slug = 'scnu'")
        if not t_id:
            print("ERROR: tenant 'scnu' not found. Run seed_tenant.py first.")
            return
        print(f"Tenant scnu: {t_id}")

        # Find or create scnu user
        row = await conn.fetchrow("SELECT id, password_hash FROM users WHERE username = 'scnu'")
        new_hash = hash_password("scnu2026")
        if row:
            u_id = row["id"]
            print(f"User scnu exists: {u_id}. Updating password to 'scnu2026'...")
            await conn.execute(
                "UPDATE users SET password_hash = $1 WHERE id = $2::uuid",
                new_hash, u_id,
            )
            print("Password updated.")
        else:
            u_id = uuid.uuid4()
            print(f"Creating user scnu: {u_id}")
            await conn.execute(
                "INSERT INTO users (id, username, password_hash, region, score, subjects) "
                "VALUES ($1::uuid, 'scnu', $2, '', 0, '')",
                u_id, new_hash,
            )
            print("User created.")

        # Ensure tenant_users link with role='admin'
        link_id = await conn.fetchval(
            "SELECT id FROM tenant_users WHERE tenant_id = $1::uuid AND user_id = $2::uuid",
            t_id, u_id,
        )
        if link_id:
            print(f"TenantUser link exists: {link_id}. Updating role to 'admin'...")
            await conn.execute(
                "UPDATE tenant_users SET role = 'admin' WHERE id = $1::uuid",
                link_id,
            )
        else:
            link_id = uuid.uuid4()
            print(f"Creating TenantUser link: {link_id}")
            await conn.execute(
                "INSERT INTO tenant_users (id, tenant_id, user_id, role) "
                "VALUES ($1::uuid, $2::uuid, $3::uuid, 'admin')",
                link_id, t_id, u_id,
            )
        print("Link role set to 'admin'.")

        # Verify
        verify = await conn.fetchrow(
            "SELECT u.username, u.password_hash, tu.role "
            "FROM users u JOIN tenant_users tu ON tu.user_id = u.id "
            "WHERE u.username = 'scnu'"
        )
        print(f"Verification: username={verify['username']}, role={verify['role']}, hash_prefix={verify['password_hash'][:20]}...")
        print("DONE.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
