<#
.SYNOPSIS
  Instala la Skill de WheelSaver + CLI + API en el proyecto actual para que
  Claude pueda auditar el proyecto y recomendar librerias de GitHub.

.DESCRIPTION
  Copia el skill de auditoria WheelSaver, el CLI unificado (cli.py) y la API
  (api/) al proyecto activo, enlazando la base de datos centralizada.
  Despues de ejecutarlo, abre Claude Code y dile:
  "Audita este proyecto con WheelSaver"

.EXAMPLE
  & "E:\PROYECTOS\Mis_Proyectos\TOP_REPOS\Instalar-WheelSaver.ps1"
#>

$origenBase  = "E:\PROYECTOS\Mis_Proyectos\TOP_REPOS"
$origenSkill = "$origenBase\.agents\skills\wheel_saver"
$destinoSkill = "$PWD\.agents\skills\wheel_saver"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "    WheelSaver — Instalacion Rapida"          -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Proyecto destino: $PWD" -ForegroundColor White

# Validar que existe la base de WheelSaver
if (-not (Test-Path $origenSkill)) {
    Write-Host "Error: No se encuentra WheelSaver en $origenSkill" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "$origenBase\data\top_repos.db")) {
    Write-Host "Error: No se encuentra la base de datos en $origenBase\data\top_repos.db" -ForegroundColor Red
    Write-Host "Ejecuta el scraper primero: python cli.py scrape" -ForegroundColor Red
    exit 1
}

# Crear directorio destino del skill
New-Item -ItemType Directory -Force -Path $destinoSkill | Out-Null

# Copiar skill + scripts
Copy-Item -Path "$origenSkill\*" -Destination $destinoSkill -Recurse -Force

Write-Host ""
Write-Host "WheelSaver instalado con exito!" -ForegroundColor Green
Write-Host ""
Write-Host "Proximos pasos:" -ForegroundColor Yellow
Write-Host "  1. Abre Claude Code en esta carpeta:    claude" -ForegroundColor White
Write-Host "  2. Pide una auditoria:                  Audita este proyecto con WheelSaver" -ForegroundColor White
Write-Host ""
Write-Host "Comandos utiles (si tienes acceso al proyecto WheelSaver):" -ForegroundColor Gray
Write-Host "  python cli.py search <keyword>     Buscar repos" -ForegroundColor Gray
Write-Host "  python cli.py stats                Estadisticas de la BD" -ForegroundColor Gray
Write-Host "  python cli.py api                  Lanzar API REST" -ForegroundColor Gray
Write-Host ""
Write-Host "BD centralizada: $origenBase\data\top_repos.db" -ForegroundColor Gray
Write-Host "  (se actualiza cada semana via GitHub Actions)" -ForegroundColor Gray
