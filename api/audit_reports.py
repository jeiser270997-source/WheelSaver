"""api/audit_reports.py — Construcción de reportes de auditoría offline.

Extraído de api/llm.py para mantener responsabilidad única: aquí vive solo
la lógica de formateo de reportes; la orquestación LLM queda en llm.py.
"""


def build_static_analysis_summary(static_analysis: dict) -> str:
    """Resumen compacto de bandit + vulture + radon para pasarle al LLM."""
    if not static_analysis:
        return ""
    sec = static_analysis.get("security", {})
    dc = static_analysis.get("dead_code", {})
    cx = static_analysis.get("complexity", {})

    static_parts = []
    if sec.get("available"):
        sev = sec.get("by_severity", {})
        total = sec.get("total_findings", 0)
        static_parts.append(
            "--- Seguridad (bandit) ---\n"
            f"Hallazgos totales: {total}\n"
            f"HIGH: {sev.get('HIGH', 0)} | MEDIUM: {sev.get('MEDIUM', 0)} | LOW: {sev.get('LOW', 0)}"
        )
        top = sec.get("top_findings", [])
        if top:
            static_parts.append("Top hallazgos:")
            for f in top:
                static_parts.append(
                    f"  - {f.get('file', '')}:{f.get('line', '')} "
                    f"[{f.get('severity', '')}] {f.get('issue', '')[:100]}"
                )

    if dc.get("available"):
        total = dc.get("total_findings", 0)
        static_parts.append(f"--- Código Muerto (vulture) ---\nHallazgos: {total}")

    if cx.get("available"):
        total = cx.get("high_complexity_count", 0)
        static_parts.append(f"--- Complejidad Ciclomática (radon) ---\nFunciones con rango D/E/F: {total}")

    return "\n\n## Resultados de Análisis Estático\n\n" + "\n\n".join(static_parts) if static_parts else ""


def build_offline_audit_report(audit_data: dict, missing_categories: list, static_analysis: dict) -> str:
    """Informe de auditoría 100% offline (sin LLM) cuando no hay proveedores."""
    report_lines = [
        "### 🛞 WheelSaver — Informe de Auditoría Local (Modo 100% Offline)",
        f"**Stack**: {audit_data['stack_str']} | **Framework**: {audit_data['framework'] or 'No detectado'}\n",
    ]
    if missing_categories:
        report_lines.append("**Componentes Faltantes Recomendados:**")
        for label, cat, keywords in missing_categories:
            report_lines.append(
                f"- **{label}** (Categoría: `{cat}`): Se sugiere instalar librerías para `{keywords}`"
            )
        report_lines.append("")
    else:
        report_lines.append("✅ **Todos los checks básicos de la estructura están cubiertos.**\n")

    if static_analysis:
        sec = static_analysis.get("security", {})
        dc = static_analysis.get("dead_code", {})
        cx = static_analysis.get("complexity", {})
        report_lines.append("**Resultados de Análisis Estático Local (Bandit + Vulture + Radon):**")
        if sec.get("available"):
            sev = sec.get("by_severity", {})
            report_lines.append(
                f"- 🔐 **Seguridad (bandit)**: {sec.get('total_findings', 0)} hallazgos "
                f"(HIGH: {sev.get('HIGH', 0)}, MEDIUM: {sev.get('MEDIUM', 0)}, LOW: {sev.get('LOW', 0)})"
            )
        if dc.get("available"):
            report_lines.append(
                f"- 🧹 **Código Muerto (vulture)**: {dc.get('total_findings', 0)} variables/funciones sin uso"
            )
        if cx.get("available"):
            report_lines.append(
                f"- ⚡ **Complejidad (radon)**: {cx.get('high_complexity_count', 0)} "
                f"funciones con alta complejidad ciclomática (rango D/E/F)"
            )

    report_lines.append(
        "\n[dim]Nota: Para profundizar con RAG multi-proveedor, configura una API key en tu .env "
        "(GROQ_API_KEY, GOOGLE_API_KEY, etc.)[/dim]"
    )
    return "\n".join(report_lines)
