"""Unit tests for module registry — dependency chain and gating logic."""
import pytest
from core.module_registry import ModuleKey, MODULE_DEPENDENCIES, check_module_enabled


class FakeTenant:
    def __init__(self, modules: dict):
        self.config = {"modules": modules}


def test_module_with_no_dependencies_passes():
    tenant = FakeTenant({"funnel": True})
    check_module_enabled(tenant, ModuleKey.FUNNEL)  # should not raise


def test_module_not_enabled_raises_403():
    tenant = FakeTenant({"funnel": False})
    with pytest.raises(Exception) as exc:
        check_module_enabled(tenant, ModuleKey.FUNNEL)
    assert exc.value.status_code == 403
    assert "not enabled" in exc.value.detail


def test_competitive_analysis_requires_funnel_and_profile():
    deps = MODULE_DEPENDENCIES[ModuleKey.COMPETITIVE_ANALYSIS]
    assert ModuleKey.FUNNEL in deps
    assert ModuleKey.PROFILE_DASHBOARD in deps


def test_competitive_analysis_passes_when_all_deps_enabled():
    tenant = FakeTenant({
        "funnel": True,
        "profile_dashboard": True,
        "competitive_analysis": True,
    })
    check_module_enabled(tenant, ModuleKey.COMPETITIVE_ANALYSIS)  # ok


def test_competitive_analysis_fails_when_dep_missing():
    tenant = FakeTenant({
        "funnel": True,
        "profile_dashboard": False,
        "competitive_analysis": True,
    })
    with pytest.raises(Exception) as exc:
        check_module_enabled(tenant, ModuleKey.COMPETITIVE_ANALYSIS)
    assert "requires" in exc.value.detail
    assert "profile_dashboard" in exc.value.detail


def test_annual_report_requires_five_deps():
    deps = MODULE_DEPENDENCIES[ModuleKey.ANNUAL_REPORT]
    assert len(deps) == 5
    assert ModuleKey.FUNNEL in deps
    assert ModuleKey.PROFILE_DASHBOARD in deps
    assert ModuleKey.MAJOR_HEATMAP in deps
    assert ModuleKey.REGION_DISTRIBUTION in deps
    assert ModuleKey.COMPETITIVE_ANALYSIS in deps


def test_independent_module_has_no_deps():
    # These modules should have no dependencies
    assert ModuleKey.REGION_DISTRIBUTION not in MODULE_DEPENDENCIES
    assert ModuleKey.DIALOGUE_QUALITY not in MODULE_DEPENDENCIES
    assert ModuleKey.MULTI_DEPARTMENT not in MODULE_DEPENDENCIES
    assert ModuleKey.ROLE_MANAGEMENT not in MODULE_DEPENDENCIES
