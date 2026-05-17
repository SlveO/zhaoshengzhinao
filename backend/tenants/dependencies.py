"""FastAPI dependency overrides — re-export from core for convenience."""
from core.tenant_context import get_current_tenant, get_current_tenant_user  # noqa: F401
