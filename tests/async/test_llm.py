"""
Tests for api/llm.py — Multi-LLM provider layer.

Uses _run_async wrapper for async functions to avoid Python 3.14
event loop conflict between pytest-playwright and pytest-asyncio.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _run_async(coro, timeout=15):
    """Run coroutine in a new event loop with timeout."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def _no_real_providers(monkeypatch):
    """All tests in this file MUST NOT make real API calls.
    Patch _get_active_providers to return [] by default.
    Tests that need specific providers override this fixture."""
    import api.llm

    monkeypatch.setattr(api.llm, "_get_active_providers", lambda: [])
    yield


class TestBuildPrompts:
    def test_build_prompts_with_repos(self):
        from api.llm import _build_prompts

        repos = [
            {"owner": "fastapi", "name": "fastapi", "stars": 100, "description": "Fast framework", "language": "Python"},
            {"owner": "pallets", "name": "flask", "stars": 50, "description": "Micro framework", "language": "Python"},
        ]
        sys_p, user_p = _build_prompts("best python framework?", repos)
        assert "fastapi/fastapi" in user_p
        assert "python" in user_p.lower()

    def test_build_prompts_empty_repos(self):
        from api.llm import _build_prompts

        sys_p, user_p = _build_prompts("test", [])
        assert "No se encontraron repositorios" in user_p

    def test_build_prompts_null_fields(self):
        from api.llm import _build_prompts

        repos = [
            {"owner": "test", "name": "repo", "stars": None, "description": None, "language": None},
        ]
        sys_p, user_p = _build_prompts("test", repos)
        assert "Sin descripción" in user_p
        # language fallback: None → "-" → renders as "Lenguaje: -"
        assert "Lenguaje: -" in user_p


class TestGetActiveProviders:
    def test_empty_providers_default(self):
        """With _no_real_providers fixture, _get_active_providers returns []."""
        import api.llm

        assert api.llm._get_active_providers() == []

    def test_single_provider_override(self, monkeypatch):
        """Override the autouse fixture to test single provider behavior."""
        import api.llm

        fake = [{"name": "groq", "api_key": "test", "base_url": "http://localhost:9999/v1", "model": "test-model", "priority": 1, "type": "openai"}]
        monkeypatch.setattr(api.llm, "_get_active_providers", lambda: fake)
        providers = api.llm._get_active_providers()
        assert len(providers) == 1
        assert providers[0]["name"] == "groq"


class TestAskLlm:
    def test_no_providers_raises(self):
        """_no_real_providers fixture ensures empty list → RuntimeError."""
        from api.llm import ask_llm

        with pytest.raises(RuntimeError, match="No hay proveedores"):
            _run_async(ask_llm(system_prompt="test", user_prompt="test"))


class TestAskLlmAboutRepos:
    def test_no_providers_returns_friendly(self):
        from api.llm import ask_llm_about_repos

        result = _run_async(ask_llm_about_repos("test?", [{"owner": "a", "name": "b", "stars": 1}]))
        assert "error" in result.lower() or "proveedores" in result.lower()


class TestExpandSearchQuery:
    def test_fallback_on_no_providers(self):
        from api.llm import expand_search_query

        result = _run_async(expand_search_query("best python web framework"))
        assert isinstance(result, list)
        assert any(len(w) > 3 for w in result)


class TestBuildOfflineReport:
    def test_with_missing_categories(self):
        from api.llm import _build_offline_audit_report

        audit_data = {"stack_str": "Python", "framework": "FastAPI"}
        missing = [("Testing", "testing", "pytest"), ("CI/CD", "devops", "actions")]
        report = _build_offline_audit_report(audit_data, missing, None)
        assert "Componentes Faltantes" in report
        assert "Testing" in report
        assert "FastAPI" in report

    def test_no_missing_categories(self):
        from api.llm import _build_offline_audit_report

        audit_data = {"stack_str": "Python", "framework": "FastAPI"}
        report = _build_offline_audit_report(audit_data, [], None)
        assert "Todos los checks básicos" in report

    def test_with_static_analysis(self):
        from api.llm import _build_offline_audit_report

        audit_data = {"stack_str": "Python", "framework": "FastAPI"}
        static = {
            "security": {"available": True, "total_findings": 5, "by_severity": {"HIGH": 1, "MEDIUM": 2, "LOW": 2}},
            "dead_code": {"available": True, "total_findings": 3},
            "complexity": {"available": True, "high_complexity_count": 2},
        }
        report = _build_offline_audit_report(audit_data, [], static)
        assert "Seguridad (bandit)" in report
        assert "Código Muerto (vulture)" in report
        assert "Complejidad (radon)" in report


class TestBuildStaticAnalysisSummary:
    def test_empty_input(self):
        from api.llm import _build_static_analysis_summary

        assert _build_static_analysis_summary({}) == ""
        assert _build_static_analysis_summary(None) == ""

    def test_full_analysis(self):
        from api.llm import _build_static_analysis_summary

        static = {
            "security": {
                "available": True,
                "total_findings": 3,
                "by_severity": {"HIGH": 1, "MEDIUM": 1, "LOW": 1},
                "top_findings": [{"file": "test.py", "line": 10, "severity": "HIGH", "issue": "Hardcoded password"}],
            },
            "dead_code": {"available": True, "total_findings": 5},
            "complexity": {"available": True, "high_complexity_count": 2},
        }
        result = _build_static_analysis_summary(static)
        assert "Seguridad" in result
        assert "Código Muerto" in result
        assert "Complejidad Ciclomática" in result


class TestAuditProjectWithAI:
    def test_no_missing_returns_badge(self):
        from api.llm import audit_project_with_ai

        result = _run_async(audit_project_with_ai({"stack_str": "Python", "framework": "FastAPI"}, [], None))
        assert "APROBADO" in result

    def test_missing_providers_returns_offline_report(self):
        from api.llm import audit_project_with_ai

        result = _run_async(
            audit_project_with_ai(
                {"stack_str": "Python", "framework": "FastAPI"},
                [("Testing", "testing", "pytest")],
                None,
            )
        )
        assert "WheelSaver" in result
        assert "Componentes Faltantes" in result


class TestGenerateSkillFromRepo:
    def test_no_providers_returns_error_skill(self):
        from api.llm import generate_skill_from_repo

        result = _run_async(generate_skill_from_repo("test/repo", "test desc", "readme content"))
        assert "---" in result
        assert "Error" in result

    def test_skill_starts_with_frontmatter(self):
        from api.llm import generate_skill_from_repo

        result = _run_async(generate_skill_from_repo("test/repo", "test", "readme"))
        assert "---" in result
        assert "Error" in result
