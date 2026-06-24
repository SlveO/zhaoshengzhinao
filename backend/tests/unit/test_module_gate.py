import pytest
from fastapi import HTTPException

from core.module_registry import ModuleKey, check_module_enabled


class Tenant:
    def __init__(self, modules):
        self.config = {"modules": modules}


def test_module_gate_allows_enabled_module():
    tenant = Tenant({"profile_dashboard": True})

    check_module_enabled(tenant, ModuleKey.PROFILE_DASHBOARD)


def test_module_gate_blocks_disabled_module():
    tenant = Tenant({"profile_dashboard": False})

    with pytest.raises(HTTPException) as exc:
        check_module_enabled(tenant, ModuleKey.PROFILE_DASHBOARD)

    assert exc.value.status_code == 403


def test_module_gate_enforces_dependencies():
    tenant = Tenant({"competitive_analysis": True, "profile_dashboard": False})

    with pytest.raises(HTTPException) as exc:
        check_module_enabled(tenant, ModuleKey.COMPETITIVE_ANALYSIS)

    assert "profile_dashboard" in exc.value.detail
