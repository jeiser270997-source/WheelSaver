---
name: wheel-swap
description: Cuando el usuario esta codeando algo manualmente, busca si ya existe una libreria que lo haga mejor, mas rapido y con menos bugs.
---

# wheel-swap — No reinventes la rueda

Cuando el usuario diga frases como "estoy construyendo X", "hay algo para Y",
"no quiero codear esto a mano", "wheel-swap esto", ejecuta este flujo.

---

## PASO 1 — Entender que esta codeando

El usuario te dira algo como:
- "Estoy escribiendo un parser de PDF" → keyword: `pdf parser`
- "Voy a hacer autenticacion con JWT" → keyword: `auth jwt`
- "Necesito un cliente HTTP" → keyword: `http client requests`
- "Voy a mostrar graficos en el dashboard" → keyword: `charting dashboard`
- "Estoy haciendo un CLI con argumentos" → keyword: `cli argument-parser`

Si el usuario muestra codigo, leelo para entender exactamente QUE esta construyendo.

---

## PASO 2 — Generar keywords precisas

De lo que el usuario esta codeando, extrae 3-5 keywords en ingles.
Se especifico, no generico.

| Si codea... | Keywords |
|---|---|
| Un parser de CSV | `csv parser parsing` |
| Autenticacion con redes sociales | `oauth social-login passport` |
| Un sistema de colas de tareas | `task-queue celery bull rabbitmq` |
| Validacion de formularios | `form-validation zod joi yup` |
| Un ORM para SQL | `orm sqlalchemy prisma drizzle` |
| Una API REST | `rest-api fastapi express flask` |
| Un sistema de archivos | `file-upload storage s3 minio` |
| Charts/graficos | `charting d3 chart.js recharts` |
| Un crawler/scraper | `scraping crawler playwright puppeteer` |
| Notificaciones push | `push-notification websocket socket.io` |

---

## PASO 3 — Buscar en la BD

```
python cli.py search <keywords> --limit 10
```

Filtra resultados:
- Descarta los que ya usa el proyecto
- Prioriza los del mismo lenguaje
- Prioriza los mas estrellados
- Si hay 3 opciones similares, recomienda la mejor (mas estrellas + activa)

---

## PASO 4 — Hacer la recomendacion

Formato:

```markdown
## wheel-swap: [lo que estas construyendo]

❌ Estas codeando: [descripcion de lo que hace manualmente]
✅ Podrias usar: **[recomendacion]** ([N]⭐)

**Por que**: [explicacion concreta]
**Instalacion**: `pip install X` / `npm install X`
**Documentacion**: https://github.com/owner/repo

### Alternativas:
- [alt1] — [N]⭐ — [cuando elegir esta]
- [alt2] — [N]⭐ — [cuando elegir esta]

### Veredicto:
[Recomendacion final clara: "USA ESTA", "SIGUE CODEANDO" o "MIRA ESTAS 2 OPCIONES"]
```

---

## Reglas de oro
1. **Si la libreria existe y es madura (+10k⭐) → recomendarla siempre**
2. **Si es un skill/core del negocio → tal vez si conviene codearlo**
3. **Si es boilerplate/infra → siempre usar libreria**
4. **Si no hay nada en la BD que calce perfecto → decirlo honestamente**
5. **Siempre dar el comando exacto de instalacion**
