"""
defensive_scans.py — Escaneo defensivo de secretos y code smells (SRP) en código fuente.

Módulo independiente de las herramientas externas (bandit/vulture/radon):
funciona 100% offline y sin dependencias, recorriendo el árbol de archivos
buscando patrones de secretos hardcodeados y archivos que violan SRP (>300 líneas).
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Patrones para escaneo defensivo de secretos y leaks en código fuente
SECRET_PATTERNS = [
    (r"ghp_[A-Za-z0-9_]{36}", "GitHub Personal Access Token (PAT)"),
    (r"sk-proj-[A-Za-z0-9_-]{20,}", "OpenAI API Key"),
    (r"AIzaSy[A-Za-z0-9_-]{33}", "Google Cloud / Firebase API Key"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"-----BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY-----", "Clave Privada RSA / SSH"),
    (r"(postgres|mysql|mongodb|redis)://[^:]+:[^@]+@", "URI de Conexión DB con Password Hardcodeado"),
]

EXCLUDE_DIRS = {".git", ".venv", "venv", "node_modules", "data", ".audit", "__pycache__", ".pytest_cache", "build", "dist"}


def _scan_secrets(target: Path) -> dict:
    """Escanea el código fuente buscando secretos, llaves hardcodeadas y archivos sensibles."""
    findings = []
    env_in_git = False

    if not target.exists():
        return {"available": True, "total_findings": 0, "top_findings": [], "env_in_git": False}

    # Verificar si .env está rastreado por git
    if (target / ".git").exists():
        # Import perezoso para evitar ciclo: static_analyzer importa este módulo
        from services.static_analyzer import _run_tool

        code, stdout, _ = _run_tool(["git", "ls-files", ".env"], cwd=target)
        if code == 0 and stdout.strip():
            env_in_git = True
            findings.append({
                "file": ".env",
                "line": 1,
                "severity": "CRITICAL",
                "issue": "Archivo .env commitado / rastreado en Git (Zero-Leak Violation)"
            })

    # Escanear archivos fuente
    for filepath in target.rglob("*"):
        if not filepath.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in filepath.parts):
            continue
        if filepath.suffix not in {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yml", ".yaml", ".env", ".toml"}:
            continue

        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            rel_path = str(filepath.relative_to(target))

            for line_idx, line in enumerate(lines, 1):
                if len(line) > 1000:
                    continue  # Ignorar minificados
                for pattern, desc in SECRET_PATTERNS:
                    if re.search(pattern, line):
                        # Sanitizar snippet para log safe
                        sanitized_line = line[:40] + "..." if len(line) > 40 else line
                        findings.append({
                            "file": rel_path,
                            "line": line_idx,
                            "severity": "HIGH",
                            "issue": f"Secreto Detectado ({desc}): {sanitized_line}"
                        })
                        if len(findings) >= 20:
                            break
        except (OSError, UnicodeError) as e:
            # Archivos binarios/inaccesibles se ignoran silenciosamente
            logger.debug("No se pudo escanear %s: %s", filepath, e)

    return {
        "available": True,
        "total_findings": len(findings),
        "env_in_git": env_in_git,
        "top_findings": findings[:10]
    }


def _scan_code_smells(target: Path) -> dict:
    """Escanea violaciones de SRP (>300 líneas por archivo) y métricas de complejidad basales."""
    large_files = []
    total_files = 0
    total_lines = 0

    if not target.exists():
        return {"available": True, "large_files_count": 0, "top_large_files": []}

    for filepath in target.rglob("*"):
        if not filepath.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in filepath.parts):
            continue
        if filepath.suffix in {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".cpp", ".c", ".h"}:
            total_files += 1
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                lines = len(content.splitlines())
                total_lines += lines
                rel_path = str(filepath.relative_to(target))

                if lines > 300:
                    large_files.append({
                        "file": rel_path,
                        "lines": lines,
                        "issue": f"SRP Violation (>300 líneas: {lines} L) — Refactorizar en submódulos"
                    })
            except (OSError, UnicodeError) as e:
                logger.debug("No se pudo medir %s: %s", filepath, e)

    large_files.sort(key=lambda x: x["lines"], reverse=True)

    return {
        "available": True,
        "total_files": total_files,
        "total_lines": total_lines,
        "large_files_count": len(large_files),
        "top_large_files": large_files[:10]
    }
