from pathlib import Path


def detect_stack_and_framework(target: Path) -> dict:
    has_python = (
        (target / "requirements.txt").exists()
        or (target / "pyproject.toml").exists()
        or (target / "Pipfile").exists()
    )
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
    if has_js and (target / "package.json").exists():
        import json

        try:
            pkg = json.loads((target / "package.json").read_text(encoding="utf-8"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                framework = "Next.js"
            elif "react" in deps:
                framework = "React"
            elif "vue" in deps:
                framework = "Vue"
            elif "svelte" in deps:
                framework = "Svelte"
            elif "express" in deps:
                framework = "Express"
            has_tests = has_tests or "jest" in deps or "vitest" in deps or "cypress" in deps
            has_ci = has_ci or "husky" in deps or "lint-staged" in deps
        except Exception:
            pass
    elif has_python and (target / "requirements.txt").exists():
        content = (target / "requirements.txt").read_text(encoding="utf-8").lower()
        if "fastapi" in content:
            framework = "FastAPI"
        elif "django" in content:
            framework = "Django"
        elif "flask" in content:
            framework = "Flask"
        has_tests = has_tests or "pytest" in content

    stacks = []
    if has_python:
        stacks.append("Python")
    if has_js:
        stacks.append("JavaScript/TypeScript")
    if has_rust:
        stacks.append("Rust")
    if has_go:
        stacks.append("Go")

    # Static analysis (solo si es Python — silencioso si falla)
    static_analysis = None
    if has_python:
        try:
            from services.static_analyzer import analyze_python_project

            static_analysis = analyze_python_project(target)
        except ImportError:
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
