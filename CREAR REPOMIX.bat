@echo off
title Generar Repomix Actualizado
color 0B

echo ===================================================
echo      Generador de Repomix (Asistente Personal)
echo ===================================================
echo.

:: 1. Asegurar que el script se ejecute en la carpeta donde esta guardado
cd /d "%~dp0"

:: 2. Eliminar cualquier archivo repomix generado anteriormente
echo [*] Limpiando versiones anteriores...
del /q repomix_*.md 2>nul

:: 3. Generar un hash unico basado en la fecha y hora exacta
for /f "delims=" %%i in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set HASH=%%i
set OUTPUT_FILE=repomix_%HASH%.md

:: 4. Ejecutar Repomix
echo [*] Generando nuevo empaquetado en formato Markdown...
echo [*] Archivo destino: %OUTPUT_FILE%
echo [*] Por favor espera...
echo.

:: Usamos npx para asegurar que use la ultima version de repomix
call npx repomix --output %OUTPUT_FILE%

echo.
echo ===================================================
echo [OK] Proceso finalizado con exito.
echo [OK] Tu proyecto esta empaquetado en: %OUTPUT_FILE%
echo ===================================================
pause