# OPORTUNIDADES DE MEJORA — detectadas con WHEELSAVER (2026-08-15)

> Búsquedas reales contra `data/top_repos.db` (20,073 repos, FTS5) con `python cli.py search`.

## Para FACELESS (producción de videos)

### 1. 🎙️ GPT-SoVITS (60,091⭐, Python) — candidato a 1er fallback de voz
- Qué es: clonación de voz local few-shot; con **1 min de audio** entrena un TTS
  de calidad superior a Coqui XTTS v2.
- Aplicación: la cadena de voz actual es `coqui → rt-voice-cloning → kokoro →
  edge-tts`. GPT-SoVITS encajaría como fallback local de nivel 1 (mismo
  `voz_clon.wav`), mejorando realismo cuando coqui falle.
- Costo: $0, local, GPU GTX 1660 SUPER compatible (inferencia ligera).
- Riesgo: dependencia Python pesada; requiere validar VRAM/tiempo de inferencia.

### 2. 📱 MoneyPrinter (13,725⭐, Python) — referencia de hooks/retención
- Qué es: automatiza Shorts con MoviePy (guion → TTS → imágenes → video).
- Faceless usa Remotion (control frame-accurate superior, NO swap), pero
  MoneyPrinter es fuente de ideas de hooks/variaciones de formato para el skill
  `horror.md` y la validación de retención >60%.

### 3. ✅ faster-whisper (21,199⭐) — confirmado estándar (ya en uso)
- Faceless (`generate_whisper.py`) y Scrapper (`whisper_transcriber.py`) ya lo
  usan. Nada que cambiar.

## Para SCRAPPER (agente de búsqueda)

### 1. 🆔 dedupe (4,478⭐, Python) — dedup difuso de historias/guiones
- Qué es: fuzzy matching y record-linkage en Python (blocking + active learning).
- Aplicación: hoy `HorrorStory.source_url` (URL exacta) es la única anti-dup.
  Historias re-contadas con distinta URL/título escapan. `dedupe` (o una
  heurística ligera tipo difflib.SequenceMatcher en `content_hash` normalizado)
  detectaría duplicados semánticos antes de exportar a `faceless_queue/`.
- Alternativa $0 sin dep: `difflib` de stdlib con umbral de similitud en el
  texto normalizado — implementable en ~30 líneas en `story_harvester.py`.

### 2. 🔍 tiktok-scraper (5,130⭐) — alternativa evaluada, no necesaria
- Scrapper ya cubre TikTok con `TikTokApi` + dorks web (zero-ban). El repo es
  mantenido parcialmente; no aporta ventaja sobre el stack actual.

### 3. 📈 trendet / kneed (491/817⭐) — no aplicar
- El comando `tendencias` de Scrapper (SQL agrupado por frecuencia) ya cubre el
  caso; estas libs son para series temporales estadísticas, overkill aquí.

## Recomendación priorizada
1. **GPT-SoVITS** como fallback de voz de Faceless (impacto directo en calidad
   de audio → retención). Validar con 1 voz + 3 Shorts.
2. **Dedup difuso en Scrapper** (`difflib` stdlib, $0) para el harvester —
   evita guiones duplicados en la cola de Faceless.
3. MoneyPrinter solo como referencia creativa (cero código).

> Regla 6 respetada: ningún repo se acopla a otro; estas son oportunidades de
> evaluación, no de importación de código.
