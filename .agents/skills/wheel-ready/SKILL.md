---
name: wheel-ready
description: Escanea un proyecto y genera un checklist de lo que le falta (testing, CI, auth, monitoreo, etc.) usando la base de datos de WheelSaver.
---

# wheel-ready — Checklist de Proyecto

Cuando el usuario invoque este skill (frases como "wheel-ready", "que le falta a mi proyecto", "checklist de proyecto"), ejecuta este flujo.

---

## PASO 1 — Escanear el proyecto

Lee los archivos del proyecto:
- `package.json` / `requirements.txt` / `Cargo.toml` / `go.mod` / `pyproject.toml`
- `README.md`
- `.gitignore`
- Structure (2 niveles)

Identifica:
- ¿Qué stack usa? (Python, JS/TS, Rust, Go, etc.)
- ¿Qué framework? (FastAPI, Next.js, React, Django, etc.)
- ¿Qué ya tiene implementado? (testing, CI, auth, DB, etc.)
- ¿Qué está construyendo? (web app, CLI, API, mobile, etc.)

---

## PASO 2 — Categorias del checklist

Para cada categoria, determina si el proyecto ya lo cubre o necesita accion:

### 🔬 Testing
- ¿Tiene test framework? → si no: busca `pytest jest vitest playwright`
- ¿Tiene tests configurados? → si no: recomienda agregar baseline
- Keywords: `testing coverage mocking e2e`

### 🚀 CI/CD
- ¿Tiene `.github/workflows/`? → si no: busca `actions runner deployment`
- ¿Tiene Dockerfile? → si no: busca `docker container`
- Keywords: `ci/cd docker kubernetes deploy`

### 🔐 Auth / Seguridad
- ¿Maneja usuarios/autenticacion? → si no: busca `auth jwt oauth`
- ¿Variables de entorno? → verifica que no haya secrets hardcodeados
- Keywords: `auth jwt oauth encryption`

### 🗄️ Base de datos
- ¿Usa BD? → si no hay ORM: busca `orm prisma drizzle sqlalchemy`
- ¿Migraciones? → si no: busca `migration alembic`
- Keywords: `database orm migration cache redis`

### 📊 Monitoreo / Logging
- ¿Tiene logging estructurado? → si no: busca `logging opentelemetry`
- Keywords: `monitoring logging observability prometheus`

### 📱 UI (si aplica)
- ¿Tiene componente library? → si no: busca `ui tailwindcss shadcn`
- Keywords: `ui components design-system tailwind`

---

## PASO 3 — Buscar en la BD

Para cada categoria donde falte algo, ejecuta:
```
python cli.py search <keywords> --limit 5
```

---

## PASO 4 — Generar informe

Crea `wheel-ready_[proyecto].md` con:

```markdown
# wheel-ready — [Proyecto]
> Stack: [tecnologias] | Fecha: [fecha]

## Resumen
✅ Listo: [categorias cubiertas]
❌ Falta: [categorias pendientes]

---

## Checklist

### 🔬 Testing — ❌ Falta
Recomendacion: [pytest / jest / vitest + N⭐]
```bash
pip install pytest
```
[Por que es importante: 1 parrafo]

### 🚀 CI/CD — ❌ Falta
...

### ✅ Ya tienes
- [x] Variables de entorno (.env)
- [x] README documentado
...

---

## Prioridad
1. 🔴 Testing — sin tests no sabes si funciona
2. 🟡 CI/CD — para deploy seguro
3. 🟢 Auth — si manejas usuarios
```
"""

---

## Notas
- Si el proyecto YA tiene todo, felicita al usuario
- Si falta TODO, recomendacion: testing + CI primero
- No recomiendes cosas que ya usa el proyecto
- Prioriza siempre testing y CI antes que features
