@echo off
setlocal EnableDelayedExpansion
title Generador de Repomix (split nativo, auto-tamano) - v4
color 0B

:: ==========================================================
::  REPOMIX CHUNKER - v4 (splitter nativo + auto-reintento)
::  - Usa "--split-output" de Repomix (nunca corta un archivo
::    a la mitad, es la propia herramienta la que decide).
::  - Si una carpeta de primer nivel es mas grande que el
::    tamano de parte pedido, Repomix falla en vez de generar
::    una parte mas grande (lo vimos en la practica: carpeta
::    "scripts" de 550KB con un limite de 300KB). Este script
::    detecta ESE error puntual y duplica el tamano de parte
::    automaticamente hasta que entre, sin ajustar nada a mano
::    por repo.
:: ==========================================================

:: --- CONFIG ---
:: Tamano inicial por parte, en KB. Subilo si tus repos suelen
:: tener carpetas de primer nivel grandes (ahorras reintentos).
set /a PART_SIZE_KB=400
:: Cuantas veces duplicar el tamano antes de rendirse
:: (400 -> 800 -> 1600 -> 3200 -> 6400 -> 12800 KB = 12.8MB tope)
set /a MAX_ATTEMPTS=6

:: --- Repo a analizar: primer argumento, o el directorio actual ---
set "TARGET_DIR=%~1"
if "%TARGET_DIR%"=="" set "TARGET_DIR=."

:: La salida siempre queda junto al .bat, no dentro del repo analizado
set "OUT_DIR=%~dp0repomix_parts"
set "OUT_BASENAME=parte.md"
set "LOG_FILE=%~dp0repomix_last_run.log"

echo ==========================================================
echo   REPOMIX CHUNKER - v4 (split nativo + auto-tamano)
echo ==========================================================
echo   Repo objetivo   : %TARGET_DIR%
echo   Tamano inicial  : %PART_SIZE_KB%kb (se duplica si hace falta)
echo   Carpeta salida  : %OUT_DIR%
echo ==========================================================
echo.

where npx >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro "npx". Instala Node.js: https://nodejs.org/
    pause
    exit /b 1
)

if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
mkdir "%OUT_DIR%"

set /a ATTEMPT=1

:PACK
set "PART_SIZE=%PART_SIZE_KB%kb"
echo [1/2] Empaquetando con Repomix - intento %ATTEMPT%/%MAX_ATTEMPTS%, tamano %PART_SIZE%...
call npx repomix "%TARGET_DIR%" --style markdown --output-show-line-numbers --split-output "%PART_SIZE%" --output "%OUT_DIR%\%OUT_BASENAME%" > "%LOG_FILE%" 2>&1
type "%LOG_FILE%"

findstr /C:"exceeds max size" /C:"Cannot split output" "%LOG_FILE%" >nul
if not errorlevel 1 goto SIZE_TOO_SMALL

goto CHECK_OUTPUT

:SIZE_TOO_SMALL
if %ATTEMPT% GEQ %MAX_ATTEMPTS% (
    echo.
    echo [ERROR] Ni con %PART_SIZE_KB%kb alcanza. Hay una carpeta de primer
    echo nivel demasiado grande para los %MAX_ATTEMPTS% reintentos. Opciones:
    echo   - Subi PART_SIZE_KB inicial en este script y volve a correrlo.
    echo   - Si esa carpeta es contenido no esencial ^(builds, assets,
    echo     vendored code^), excluila agregando --ignore "carpeta/**"
    echo     a la linea de "call npx repomix" de este script.
    pause
    exit /b 1
)
set /a PART_SIZE_KB=PART_SIZE_KB*2
set /a ATTEMPT+=1
echo.
echo [AVISO] Una carpeta de primer nivel no entra en el tamano actual.
echo Repomix no la puede partir, asi que subimos el tamano de parte
echo a %PART_SIZE_KB%kb y reintentamos...
echo.
goto PACK

:CHECK_OUTPUT
echo.
echo [2/2] Verificando salida...
set "COUNT=0"
for %%F in ("%OUT_DIR%\parte*.md") do set /a COUNT+=1

if %COUNT%==0 (
    echo.
    echo [ERROR] Repomix no genero ningun archivo en %OUT_DIR%.
    echo Revisa el log de arriba o en: "%LOG_FILE%"
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo  PROCESO COMPLETADO - %COUNT% parte(s) generada(s) en:
echo  %OUT_DIR%
echo  ^(tamano final de parte usado: %PART_SIZE_KB%kb^)
echo ==========================================================
dir /b "%OUT_DIR%\parte*.md"
echo.
echo  NOTA: si hay 10 o mas partes, pegalas en orden NUMERICO
echo  (parte.1, parte.2 ... parte.10), no en el orden en que las
echo  lista Windows arriba (ordena como texto: parte.10 antes
echo  que parte.2).
echo.
echo  Cada parte respeta limites de archivo: Repomix nunca corta
echo  uno a la mitad. Pega el contenido de cada parte, en orden,
echo  en el chat de tu IA.
echo ==========================================================
echo.
pause