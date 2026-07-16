@echo off
title Generar Repomix Actualizado
color 0B

echo ===================================================
echo      Generador de Repomix (Asistente Personal)
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Limpiar empaquetados anteriores de Repomix
echo [*] Eliminando empaquetados anteriores para evitar duplicados...
if exist repomix_*.md (
    del /q repomix_*.md
    echo [✓] Limpieza completada.
)
echo.

:: 2. Obtener marca de tiempo de forma segura (Formato: AAAAMMDD_HHMMSS)
for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"`) do set "TS=%%a"

set "FILENAME=repomix_%TS%.md"

:: 3. Ejecutar el empaquetador
echo [*] Generando nuevo empaquetado: %FILENAME%...
echo [*] Por favor espera...
echo.

call npx repomix --output %FILENAME%

echo.
echo ===================================================
echo [OK] Proceso finalizado con exito.
echo [OK] Tu proyecto esta empaquetado en: %FILENAME%
echo ===================================================
pause