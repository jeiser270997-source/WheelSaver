# WheelSaver Audit — WheelSaver (v3.1 self-audit)
> Auditado el 2026-07-08 | 22,940 repos en la base de datos

## Lo que hizo WheelSaver desde la ultima auditoria

En la auditoria anterior detectamos 8 carencias. **Se implementaron todas**:

| Carencia | Estado | Herramienta |
|---|---|---|
| Tests | ✅ 18 tests (pytest) | pytest |
| CLI unificado | ✅ cli.py con 9 comandos | Typer + Rich |
| HTTP moderno | ✅ httpx reemplazo requests | httpx |
| Barras progreso | ✅ tqdm en importadores | tqdm |
| API REST | ✅ FastAPI con 6 endpoints | FastAPI |
| Skill potenciado | ✅ Matriz scoring, categorias, checklist | SKILL.md v3 |
| wheel-ready | ✅ Checklist de proyecto | Nuevo skill |
| wheel-swap | ✅ Busca alternativas a lo que codeas | Nuevo skill |

## Que AUN le falta (nuevas carencias detectadas)

| Carencia | Prioridad | Keywords en BD |
|---|---|---|
| Dockerizar la app | 🔴 Alta | `docker container compose` |
| Dashboard web UI | 🟡 Media | `dashboard frontend react streamlit` |
| Logging estructurado | 🟡 Media | `logging python loguru` |
| Shell completion | 🟢 Baja | `click typer shell-completion` |
| Publicar en PyPI | 🟢 Baja | `poetry build publish pypi` |

---

## Recomendaciones

### 1. Docker — moby (71,803⭐)
**URL**: https://github.com/moby/moby  
**Prioridad**: 🔴 Alta  
**Por que**: Tener Dockerfile + docker-compose.yml haria que cualquier persona
pueda levantar WheelSaver sin instalar Python ni dependencias.  
**Archivos a crear**:
```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "cli.py", "api"]
```
```yaml
# docker-compose.yml
version: '3'
services:
  wheelsaver:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    command: python cli.py api --host 0.0.0.0
```

### 2. Dashboard Web — streamlit (37,900⭐) / shadcn-ui (118,385⭐)
**URL**: https://github.com/streamlit/streamlit | https://github.com/shadcn-ui/ui  
**Prioridad**: 🟡 Media  
**Por que**: La API existe pero no hay interfaz visual. Un dashboard Streamlit
seria instantaneo para explorar la BD desde el navegador.  
**Archivo a crear**: `dashboard.py`
```python
import streamlit as st
from scraper.db_manager import get_stats, search_repos

st.title("WheelSaver Dashboard")
st.metric("Total Repos", get_stats()["total_repos"])
q = st.text_input("Buscar")
if q:
    st.dataframe(search_repos(q, limit=20))
```

### 3. Logging — loguru (21,000⭐)
**URL**: https://github.com/Delgan/loguru  
**Prioridad**: 🟡 Media  
**Por que**: Hoy WheelSaver usa `print()` mezclado con `console.print()`.
Loguru agregaria niveles (info, warning, error), rotacion de archivos,
y formato consistente.  
**Instalacion**: `pip install loguru`

### 4. Shell Completion (nativo de Typer)
**Prioridad**: 🟢 Baja  
**Por que**: Typer ya lo soporta nativamente. Un comando y tienes autocomplete:
```bash
python cli.py --install-completion
```

### 5. PyPI / pip install
**Prioridad**: 🟢 Baja  
**Por que**: `pip install wheelsaver` permitiria usar el CLI desde cualquier
parte sin necesidad de clonar el repo.  
**Herramienta**: `poetry` (34,289⭐) o `uv` (87,202⭐)

---

## Quick Wins (alto impacto, bajo esfuerzo)
1. **Dockerfile** — ~15 minutos, impacto alto (portabilidad total)
2. **Shell completion** — 1 comando (`python cli.py --install-completion`)
3. **Logging** con loguru — ~30 minutos, reemplazar print() en los 5 modulos

## Arquitectura (cambios estructurales)
1. **Dashboard web** — ~2 horas con Streamlit, agregaria valor visual inmediato
2. **Publicar en PyPI** — ~1 hora con poetry/uv, habilita `pip install wheelsaver`

## Deuda Tecnica (riesgos a futuro)
1. **Solo 18 tests** — Cubren lo basico pero no el scraper ni los importers
2. **PYTHONPATH manual** — Los scripts siguen usando `sys.path.insert(0, ...)`
3. **Sin Docker** — Si alguien nuevo quiere probarlo, tiene que instalar Python manualmente

---

## Resumen
**Antes** (v2.0): 8 carencias graves (sin tests, sin CLI, sin API, etc.)  
**Ahora** (v3.1): 5 carencias menores (Docker, dashboard, logging, completion, PyPI)  

**Progreso**: 8/8 mejoras implementadas ✅  
**Siguiente paso recomendado**: Dockerizar para portabilidad total 🐳
