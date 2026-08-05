import json
from pathlib import Path


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
        ]:
            if fw_key in deps:
                framework = fw_name
                break

        has_tests = has_tests or any(k in deps for k in ("jest", "vitest", "cypress"))
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

    has_tests = has_tests or ("pytest" in content or "unittest" in content)
    return framework, has_tests


def detect_stack_and_framework(target: Path) -> dict:
    has_python = any((target / f).exists() for f in ["requirements.txt", "pyproject.toml", "Pipfile"])
    has_js = (target / "package.json").exists()
    has_rust = (target / "Cargo.toml").exists()
    has_go = (target / "go.mod").exists()

    has_docker = (target / "Dockerfile").exists() or (target / "docker-compose.yml").exists()
    has_ci = (target / ".github" / "workflows").exists()
    has_tests = any((target / d).exists() for d in ["tests", "test", "__tests__", "spec"])
    has_readme = (target / "README.md").exists()
    has_git = (target / ".git").exists()
    has_env = (target / ".env").exists() or (target / ".env.example").exists()
    has_gitignore = (target / ".gitignore").exists()

    framework = ""
    if has_js:
        framework, has_tests, has_ci = _detect_js_framework(target, has_tests, has_ci)
    elif has_python:
        framework, has_tests = _detect_python_framework(target, has_tests)

    stacks = []
    if has_python:
        stacks.append("Python")
    if has_js:
        stacks.append("JavaScript/TypeScript")
    if has_rust:
        stacks.append("Rust")
    if has_go:
        stacks.append("Go")

    # Static analysis (solo si es Python)
    static_analysis = None
    if has_python:
        try:
            from services.static_analyzer import analyze_python_project

            static_analysis = analyze_python_project(target)
        except Exception:
            pass

    return {
        "stack_str": " + ".join(stacks) if stacks else "No detectado",
        "framework": framework,
        "checks": [
            ("🔬 Testing", has_tests, "testing", "pytest jest vitest playwright"),
            ("🚀 CI/CD", has_ci, "devops", "ci/cd actions deployment"),
            ("🐳 Docker", has_docker, "devops", "docker container dockerfile"),
            ("📝 README", has_readme, "docs", "documentation readme"),
            ("🔐 .env / Secrets", has_env, "security", "dotenv environment secrets"),
            ("📋 .gitignore", has_gitignore, "git", "gitignore template"),
            ("🔧 Git", has_git, "git", "git version-control"),
        ],
        "static_analysis": static_analysis,
    }
