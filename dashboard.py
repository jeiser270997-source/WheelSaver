"""
WheelSaver Dashboard — Interfaz web para explorar la BD de repos.

Uso:
    streamlit run dashboard.py
    python cli.py dashboard
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from scraper.db_manager import get_stats, search_repos, search_repos_multi_keywords

st.set_page_config(
    page_title="WheelSaver Dashboard",
    page_icon="🛞",
    layout="wide",
)

st.title("🛞 WheelSaver Dashboard")
st.caption("Base de datos de repositorios GitHub ordenados por estrellas")

# ── Stats ──
stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Repos", f"{stats['total_repos']:,}")
col2.metric("Lenguajes", stats["languages"])
col3.metric("Estrella Max", f"{stats['stars_max']:,}")
col4.metric("Estrella Promedio", f"{stats['stars_avg']:,}")

# ── Busqueda ──
st.subheader("🔍 Buscar Repositorios")
col_q, col_l, col_s = st.columns([3, 1, 1])
with col_q:
    q = st.text_input("Keywords", placeholder="fastapi, pytest, docker...")
with col_l:
    language = st.text_input("Lenguaje (opcional)", placeholder="Python, Rust...")
with col_s:
    limit = st.number_input("Max resultados", min_value=1, max_value=100, value=10)

if q:
    keywords = [kw.strip() for kw in q.split() if kw.strip()]
    if len(keywords) == 1:
        results = search_repos(keywords[0], limit=limit * 3)
    else:
        results = search_repos_multi_keywords(keywords, limit=limit * 3)

    if language:
        results = [r for r in results if r["language"].lower() == language.lower()]
    results = results[:limit]

    if results:
        st.write(f"**{len(results)} resultados** para: {q}")
        import pandas as pd
        df = pd.DataFrame(results)
        df["stars"] = df["stars"].apply(lambda x: f"{x:,}")
        st.dataframe(
            df[["name", "owner", "stars", "language", "description"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": "Nombre",
                "owner": "Owner",
                "stars": "Estrellas",
                "language": "Lenguaje",
                "description": "Descripcion",
            },
        )
    else:
        st.info("No se encontraron resultados")

# ── Top Lenguajes ──
st.subheader("📊 Top Lenguajes")
if stats.get("top_languages"):
    import pandas as pd
    lang_df = pd.DataFrame(
        list(stats["top_languages"].items()),
        columns=["Lenguaje", "Repos"],
    )
    st.bar_chart(lang_df, x="Lenguaje", y="Repos")
    st.dataframe(lang_df, use_container_width=True, hide_index=True)

# ── Footer ──
st.divider()
st.caption(f"WheelSaver v3.2 | {stats['total_repos']:,} repos · {stats['languages']} lenguajes")
