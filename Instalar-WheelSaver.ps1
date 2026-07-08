<#
.SYNOPSIS
  Instala la Skill de WheelSaver en el proyecto actual para que Claude
  pueda auditar el proyecto y recomendar librerías de GitHub.

.DESCRIPTION
  Copia el skill de auditoría WheelSaver al proyecto activo y enlaza
  la base de datos centralizada de repos top de GitHub.
  Después de ejecutarlo, abre Claude Code y dile:
  "Audita este proyecto con WheelSaver"

.EXAMPLE
  & "E:\PROYECTOS\Mis_Proyectos\TOP_REPOS\Instalar-WheelSaver.ps1"
#>

$origenBase  = "E:\PROYECTOS\Mis_Proyectos\TOP_REPOS"
$origenSkill = "$origenBase\.agents\skills\wheel_saver"
$destinoSkill = "$PWD\.agents\skills\wheel_saver"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "    🛞 WheelSaver — Instalación Rápida"       -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📂 Proyecto destino: $PWD" -ForegroundColor White

# Validar que existe la base de WheelSaver
if (-not (Test-Path $origenSkill)) {
    Write-Host "❌ Error: No se encuentra WheelSaver en $origenSkill" -ForegroundColor Red
    Write-Host "   Verifica la ruta o clona el repositorio WheelSaver primero." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "$origenBase\data\top_repos.db")) {
    Write-Host "❌ Error: No se encuentra la base de datos en $origenBase\data\top_repos.db" -ForegroundColor Red
    Write-Host "   Ejecuta el scraper primero: python scraper/github_fetcher.py" -ForegroundColor Red
    exit 1
}

# Crear directorio destino
New-Item -ItemType Directory -Force -Path $destinoSkill | Out-Null

# Copiar skill
Copy-Item -Path "$origenSkill\*" -Destination $destinoSkill -Recurse -Force

Write-Host ""
Write-Host "✅ ¡WheelSaver instalado con éxito!" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "  1. Abre Claude Code en esta carpeta:    claude" -ForegroundColor White
Write-Host "  2. Pide una auditoría:                  Audita este proyecto con WheelSaver" -ForegroundColor White
Write-Host ""
Write-Host "ℹ️  La base de datos centralizada se encuentra en:" -ForegroundColor Gray
Write-Host "   $origenBase\data\top_repos.db" -ForegroundColor Gray
Write-Host "   (se actualiza automáticamente cada semana vía GitHub Actions)" -ForegroundColor Gray
