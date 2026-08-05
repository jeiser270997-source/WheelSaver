"""
static_analyzer.py — Análisis estático de seguridad y calidad de código.

Ejecuta herramientas de análisis estático ya existentes (bandit, vulture, radon)
sobre un proyecto Python de terceros, y condensa sus resultados en un resumen
compacto apto para pasarle a un LLM (sin necesidad de leer el código fuente
completo, evitando gastar contexto/cuota de proveedores free-tier).

Alcance actual: solo proyectos Python. Soporte para JS/TS queda pendiente
(ver FIX futuro).
"""

import json
import subprocess
from pathlib import Path


def _run_tool(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    """
    Ejecuta un comando externo con timeout defensivo y devuelve
    (returncode, stdout, stderr). Nunca lanza excepción: si el binario
    no existe o falla, se captura y se reporta como error suave.
    """
    try:
        result = subprocess.run(
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


def _run_bandit(target: Path) -> dict:
    """Ejecuta bandit (seguridad) y devuelve resumen por severidad."""
    code, stdout, stderr = _run_tool(["bandit", "-r", str(target), "-x", "tests,venv,.venv,data,.audit", "-f", "json", "-q"], cwd=target)
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


def analyze_python_project(target: Path) -> dict:
    """
    Corre bandit + vulture + radon sobre un proyecto Python y devuelve
    un resumen compacto combinado, apto para pasarle a un LLM sin exceder
    limites de contexto de proveedores free-tier.
    """
    return {
        "security": _run_bandit(target),
        "dead_code": _run_vulture(target),
        "complexity": _run_radon(target),
    }
