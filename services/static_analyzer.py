"""
static_analyzer.py — Análisis estático universal de seguridad, leaks, deuda técnica y calidad de código.

Ejecuta herramientas de análisis estático (bandit, vulture, radon) y auditoría de
dependencias en proyectos Python, JS/TS y políglotas. Los escáneres offline de
secretos y code smells (SRP) viven en services/defensive_scans.py.
"""

import json
import logging
import subprocess  # nosec B404 — análisis estático de terceros, uso legítimo
from pathlib import Path

from services.defensive_scans import (  # noqa: F401 — re-export para compatibilidad
    EXCLUDE_DIRS,
    SECRET_PATTERNS,
    _scan_code_smells,
    _scan_secrets,
)

logger = logging.getLogger(__name__)


def _run_tool(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    """
    Ejecuta un comando externo con timeout defensivo y devuelve
    (returncode, stdout, stderr).

    Seguridad: cmd es una lista de argumentos estática (sin shell=True) y
    sin interpolación de input del usuario — bandit B603/B607 no aplica.
    """
    try:
        result = subprocess.run(  # nosec B603 — lista de args, sin shell, comandos hardcodeados
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Herramienta no instalada: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", f"Timeout ejecutando: {' '.join(cmd)}"
    except Exception as e:
        return -1, "", f"Error inesperado ejecutando {cmd[0]}: {e}"


# Exclusión de bandit como patrones glob (no planos). En Windows bandit reporta
# rutas con prefijo './' (p.ej. ./tests/x.py), lo que rompe fnmatch para patrones
# planos como 'tests'. El prefijo '*/' matchea la ruta completa y funciona en
# Linux/macOS/Windows por igual.
BANDIT_EXCLUDE = "*/tests/*,*/test_ui.py,*/venv/*,*/.venv/*,*/data/*,*/.audit/*,*/__pycache__/*"


def _run_bandit(target: Path) -> dict:
    """Ejecuta bandit (seguridad Python) y devuelve resumen por severidad."""
    code, stdout, stderr = _run_tool(["bandit", "-r", str(target), "-x", BANDIT_EXCLUDE, "-f", "json", "-q"], cwd=target)
    if code == -1:
        return {"available": False, "error": stderr}

    try:
        data = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        return {"available": False, "error": "No se pudo parsear salida de bandit"}

    results = data.get("results", [])
    by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    top_findings = []
    for r in results:
        sev = r.get("issue_severity", "LOW")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        if len(top_findings) < 10:
            top_findings.append(
                {
                    "file": r.get("filename", ""),
                    "line": r.get("line_number", 0),
                    "severity": sev,
                    "issue": r.get("issue_text", "")[:150],
                }
            )

    return {
        "available": True,
        "total_findings": len(results),
        "by_severity": by_severity,
        "top_findings": top_findings,
    }


def _run_vulture(target: Path) -> dict:
    """Ejecuta vulture (código muerto) y devuelve resumen."""
    code, stdout, stderr = _run_tool(["vulture", str(target), "--min-confidence", "80"], cwd=target)
    if code == -1:
        return {"available": False, "error": stderr}

    lines = [line.strip() for line in stdout.split("\n") if line.strip()]
    return {
        "available": True,
        "total_findings": len(lines),
        "top_findings": lines[:10],
    }


def _run_radon(target: Path) -> dict:
    """Ejecuta radon (complejidad ciclomática) y devuelve funciones más complejas."""
    code, stdout, stderr = _run_tool(["radon", "cc", str(target), "-j"], cwd=target)
    if code == -1:
        return {"available": False, "error": stderr}

    try:
        data = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        return {"available": False, "error": "No se pudo parsear salida de radon"}

    high_complexity = []
    for filepath, blocks in data.items():
        for block in blocks:
            if block.get("rank", "A") in ("D", "E", "F"):
                high_complexity.append(
                    {
                        "file": filepath,
                        "name": block.get("name", ""),
                        "complexity": block.get("complexity", 0),
                        "rank": block.get("rank", ""),
                    }
                )

    high_complexity.sort(key=lambda x: x["complexity"], reverse=True)

    return {
        "available": True,
        "high_complexity_count": len(high_complexity),
        "top_findings": high_complexity[:10],
    }


def _run_js_audit(target: Path) -> dict:
    """Audita proyectos Node.js / React / Next.js (package.json)."""
    pkg_file = target / "package.json"
    if not pkg_file.exists():
        return {"available": False, "error": "No package.json"}

    try:
        pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        scripts = pkg.get("scripts", {})

        issues = []
        if "test" not in scripts:
            issues.append("Falta script 'test' en package.json")
        if "lint" not in scripts:
            issues.append("Falta script 'lint' en package.json")

        unpinned = [k for k, v in {**deps, **dev_deps}.items() if v in ("*", "latest")]
        if unpinned:
            issues.append(f"Dependencias sin versión fijada (* / latest): {', '.join(unpinned)}")

        return {
            "available": True,
            "total_dependencies": len(deps) + len(dev_deps),
            "scripts": list(scripts.keys()),
            "issues": issues
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def analyze_python_project(target: Path) -> dict:
    """
    Corre bandit + vulture + radon + escaneo de secretos y SRP sobre un proyecto Python.
    """
    return {
        "security": _run_bandit(target),
        "dead_code": _run_vulture(target),
        "complexity": _run_radon(target),
        "secrets": _scan_secrets(target),
        "code_smells": _scan_code_smells(target),
    }


def analyze_project(target: Path) -> dict:
    """
    Analizador estático universal multilenguaje (Python, JS/TS, Rust, Go, etc.).
    """
    python_analysis = analyze_python_project(target)
    js_analysis = _run_js_audit(target)
    secrets_analysis = _scan_secrets(target)
    code_smells = _scan_code_smells(target)

    return {
        "python_analysis": python_analysis,
        "js_analysis": js_analysis,
        "secrets": secrets_analysis,
        "code_smells": code_smells,
    }
