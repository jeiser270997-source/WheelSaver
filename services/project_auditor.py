import json
from pathlib import Path

from loguru import logger


def _detect_js_framework(target: Path, has_tests: bool, has_ci: bool) -> tuple[str, bool, bool]:
    pkg_file = target / "package.json"
    if not pkg_file.exists():
        return "", has_tests, has_ci

    try:
        pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        framework = ""
        for fw_key, fw_name in [
            ("next", "Next.js"),
            ("react", "React"),
            ("vue", "Vue"),
            ("svelte", "Svelte"),
            ("express", "Express"),
            ("nest", "NestJS"),
            ("fastify", "Fastify"),
        ]:
            if fw_key in deps:
                framework = fw_name
                break

        has_tests = has_tests or any(k in deps for k in ("jest", "vitest", "cypress", "playwright", "@playwright/test"))
        has_ci = has_ci or any(k in deps for k in ("husky", "lint-staged"))
        return framework, has_tests, has_ci
    except Exception:
        return "", has_tests, has_ci


def _detect_python_framework(target: Path, has_tests: bool) -> tuple[str, bool]:
    req_file = target / "requirements.txt"
    pyproject_file = target / "pyproject.toml"

    content = ""
    if req_file.exists():
        content += req_file.read_text(encoding="utf-8").lower()
    if pyproject_file.exists():
        content += "\n" + pyproject_file.read_text(encoding="utf-8").lower()

    if not content:
        return "", has_tests

    framework = ""
    if "fastapi" in content:
        framework = "FastAPI"
    elif "django" in content:
        framework = "Django"
    elif "flask" in content:
        framework = "Flask"

    has_tests = has_tests or ("pytest" in content or "unittest" in content or "robotframework" in content)
    return framework, has_tests


def detect_stack_and_framework(target: Path) -> dict:
    has_python = any((target / f).exists() for f in ["requirements.txt", "pyproject.toml", "Pipfile"])
    has_js = (target / "package.json").exists()
    has_rust = (target / "Cargo.toml").exists()
    has_go = (target / "go.mod").exists()

    has_docker = (target / "Dockerfile").exists() or (target / "docker-compose.yml").exists() or (target / "docker-compose.yaml").exists()
    has_ci = (target / ".github" / "workflows").exists()
    has_tests = any((target / d).exists() for d in ["tests", "test", "__tests__", "spec"])
    has_readme = (target / "README.md").exists()
    has_git = (target / ".git").exists()
    has_env = (target / ".env").exists() or (target / ".env.example").exists()
    has_gitignore = (target / ".gitignore").exists()

    framework = ""
    primary_language = ""
    if has_python:
        primary_language = "Python"
        framework, has_tests = _detect_python_framework(target, has_tests)
    elif has_js:
        primary_language = "JavaScript"
        framework, has_tests, has_ci = _detect_js_framework(target, has_tests, has_ci)
    elif has_rust:
        primary_language = "Rust"
    elif has_go:
        primary_language = "Go"

    stacks = []
    if has_python:
        stacks.append("Python")
    if has_js:
        stacks.append("JavaScript/TypeScript")
    if has_rust:
        stacks.append("Rust")
    if has_go:
        stacks.append("Go")

    # Keywords por lenguaje especifico para recomendaciones
    if primary_language == "Python":
        test_kw = "pytest coverage playwright"
    elif primary_language == "JavaScript":
        test_kw = "vitest jest playwright"
    else:
        test_kw = "testing e2e coverage"

    # Analisis estatico universal
    static_analysis = None
    try:
        from services.static_analyzer import analyze_project, analyze_python_project

        if has_python:
            static_analysis = analyze_python_project(target)
        else:
            static_analysis = analyze_project(target)
    except Exception as e:
        logger.debug("Análisis estático no disponible: {}", e)

    return {
        "primary_language": primary_language,
        "stack_str": " + ".join(stacks) if stacks else "No detectado",
        "framework": framework,
        "checks": [
            ("🔬 Testing", has_tests, "testing", test_kw),
            ("🚀 CI/CD", has_ci, "devops", "ci/cd actions deployment"),
            ("🐳 Docker", has_docker, "devops", "docker container dockerfile"),
            ("📝 README", has_readme, "docs", "documentation readme"),
            ("🔐 .env / Secrets", has_env, "security", "dotenv environment secrets"),
            ("📋 .gitignore", has_gitignore, "git", "gitignore template"),
            ("🔧 Git", has_git, "git", "git version-control"),
        ],
        "static_analysis": static_analysis,
    }
