"""
Tests for services/static_analyzer.py — bandit + vulture + radon wrapper.

Covers: analyze_python_project, _run_tool, _run_bandit, _run_vulture, _run_radon.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestRunTool:
    def test_tool_not_found(self):
        from services.static_analyzer import _run_tool

        code, stdout, stderr = _run_tool(["nonexistent_tool_xyz"], Path(os.path.dirname(__file__)))
        assert code == -1
        assert "no instalada" in stderr.lower() or "no encontrada" in stderr.lower() or "not found" in stderr.lower()


class TestAnalyzePythonProject:
    def test_analyze_nonexistent_path(self):
        from services.static_analyzer import analyze_python_project

        result = analyze_python_project(Path("/nonexistent/path/xyz123"))
        assert "security" in result
        assert "dead_code" in result
        assert "complexity" in result

    def test_analyze_empty_dir(self):
        from services.static_analyzer import analyze_python_project

        with tempfile.TemporaryDirectory() as tmpdir:
            result = analyze_python_project(Path(tmpdir))
            assert isinstance(result, dict)
            assert "security" in result
            assert "dead_code" in result
            assert "complexity" in result

    def test_analyze_simple_script(self):
        from services.static_analyzer import analyze_python_project

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.py"
            p.write_text("x = 1\nprint(x)\n")
            result = analyze_python_project(Path(tmpdir))
            assert isinstance(result, dict)
            # Should not crash even if bandit/vulture/radon not installed
            assert "security" in result


class TestRunBandit:
    def test_no_project(self):
        from services.static_analyzer import _run_bandit

        result = _run_bandit(Path("/nonexistent"))
        # May or may not have bandit installed
        assert "available" in result
        assert isinstance(result.get("available"), bool)


class TestRunVulture:
    def test_no_project(self):
        from services.static_analyzer import _run_vulture

        result = _run_vulture(Path("/nonexistent"))
        assert "available" in result
        assert isinstance(result.get("available"), bool)


class TestRunRadon:
    def test_no_project(self):
        from services.static_analyzer import _run_radon

        result = _run_radon(Path("/nonexistent"))
        assert "available" in result
        assert isinstance(result.get("available"), bool)
