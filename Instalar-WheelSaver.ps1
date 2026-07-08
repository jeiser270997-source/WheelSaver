<#
.SYNOPSIS
  Instala TODOS los skills de WheelSaver globalmente para usarlos desde
  cualquier proyecto. Rueditas de entrenamiento para no cagarla.

.DESCRIPTION
  Copia todos los skills (wheel-saver, wheel-ready, wheel-swap) al proyecto
  activo. Despues de ejecutar, abre Claude y usa:
  - "Audita este proyecto con WheelSaver"
  - "wheel-ready" (checklist de proyecto)
  - "wheel-swap X" (busca alternativa a lo que codeas)

.EXAMPLE
  & "E:\PROYECTOS\Mis_Proyectos\TOP_REPOS\Instalar-WheelSaver.ps1"
#>

$origenBase  = "E:\PROYECTOS\Mis_Proyectos\TOP_REPOS"
$skillsDir   = "$origenBase\.agents\skills"
$destinoSkills = "$PWD\.agents\skills"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "    WheelSaver — Rueditas de Entrenamiento"   -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Proyecto destino: $PWD" -ForegroundColor White

# Validar
if (-not (Test-Path "$origenBase\data\top_repos.db")) {
    Write-Host "Error: No se encuentra la BD en $origenBase\data\top_repos.db" -ForegroundColor Red
    exit 1
}

# Crear directorio destino
if (-not (Test-Path $destinoSkills)) {
    New-Item -ItemType Directory -Force -Path $destinoSkills | Out-Null
}

# Skills a instalar
$skills = @("wheel_saver", "wheel-ready", "wheel-swap")

foreach ($skill in $skills) {
    $origen = "$skillsDir\$skill"
    $destino = "$destinoSkills\$skill"

    if (Test-Path $origen) {
        Write-Host "  Instalando skill: $skill" -ForegroundColor Gray
        if (-not (Test-Path $destino)) {
            New-Item -ItemType Directory -Force -Path $destino | Out-Null
        }
        Copy-Item -Path "$origen\*" -Destination $destino -Recurse -Force
        Write-Host "    -> $destino" -ForegroundColor DarkGray
    } else {
        Write-Host "  [WARN] Skill no encontrado: $skill" -ForegroundColor Yellow
    }
}

# Crear alias global para CLI (opcional)
$aliasScript = @"
# WheelSaver CLI alias (agrega esto a tu `$PROFILE)
function wheelsaver {
    python E:\PROYECTOS\Mis_Proyectos\TOP_REPOS\cli.py @args
}
"@

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Rueditas instaladas con exito!"              -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Skills disponibles en este proyecto:" -ForegroundColor Yellow
Write-Host "  🛞 wheel_saver  — Auditoria completa del proyecto" -ForegroundColor White
Write-Host "  ✅ wheel-ready  — Checklist de lo que le falta" -ForegroundColor White
Write-Host "  🔄 wheel-swap   — Busca alternativa a lo que codeas" -ForegroundColor White
Write-Host ""
Write-Host "Como usarlos:" -ForegroundColor Yellow
Write-Host "  1. Abre Claude Code:               claude" -ForegroundColor Gray
Write-Host "  2. Auditar proyecto:               Audita este proyecto con WheelSaver" -ForegroundColor Gray
Write-Host "  3. Checklist:                      wheel-ready" -ForegroundColor Gray
Write-Host "  4. Buscar alternativa:             wheel-swap parser de PDF" -ForegroundColor Gray
Write-Host ""
Write-Host "CLI directo (sin Claude):" -ForegroundColor Yellow
Write-Host "  python E:\PROYECTOS\Mis_Proyectos\TOP_REPOS\cli.py search <keyword>" -ForegroundColor Gray
Write-Host "  python E:\PROYECTOS\Mis_Proyectos\TOP_REPOS\cli.py swap 'pdf parser'" -ForegroundColor Gray
Write-Host "  python E:\PROYECTOS\Mis_Proyectos\TOP_REPOS\cli.py stats" -ForegroundColor Gray
Write-Host "  python E:\PROYECTOS\Mis_Proyectos\TOP_REPOS\cli.py ready" -ForegroundColor Gray
Write-Host ""
Write-Host "BD centralizada: $origenBase\data\top_repos.db ($((Get-Item "$origenBase\data\top_repos.db").Length / 1MB) MB)" -ForegroundColor DarkGray
