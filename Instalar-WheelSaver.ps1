<#
.SYNOPSIS
  Instala WheelSaver globalmente en el sistema.

.DESCRIPTION
  Instala el paquete wheelsaver como comando global y copia los skills
  al proyecto activo para que Claude Code los reconozca.

  Ahora WheelSaver se instala via pip en modo editable (-e .) y el
  comando wheelsaver queda disponible globalmente en la terminal.

.EXAMPLE
  .\Instalar-WheelSaver.ps1
#>

$projectRoot = $PSScriptRoot
$destinoSkills = "$PWD\.agents\skills"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "    WheelSaver — Instalacion Global"           -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Proyecto origen:  $projectRoot" -ForegroundColor White
Write-Host "Proyecto destino: $PWD" -ForegroundColor White

# 1. Instalar paquete en modo editable
Write-Host ""
Write-Host "[1/3] Instalando paquete wheelsaver..." -ForegroundColor Yellow
try {
    & pip install -e "$projectRoot"
    Write-Host "  OK: wheelsaver instalado globalmente" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: No se pudo instalar el paquete" -ForegroundColor Red
    exit 1
}

# 2. Copiar skills al proyecto activo
Write-Host ""
Write-Host "[2/3] Instalando skills para Claude Code..." -ForegroundColor Yellow

if (-not (Test-Path $destinoSkills)) {
    New-Item -ItemType Directory -Force -Path $destinoSkills | Out-Null
}

$skills = @("wheel_saver", "wheel-ready", "wheel-swap")

foreach ($skill in $skills) {
    $origen = "$projectRoot\.agents\skills\$skill"
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

# 3. Verificar instalacion
Write-Host ""
Write-Host "[3/3] Verificando instalacion..." -ForegroundColor Yellow
try {
    $testVersion = & wheelsaver --help 2>&1 | Out-String
    if ($testVersion -match "WheelSaver") {
        Write-Host "  OK: Comando 'wheelsaver' disponible" -ForegroundColor Green
    }
} catch {
    Write-Host "  AVISO: No se pudo verificar el comando. Prueba 'wheelsaver --help'" -ForegroundColor Yellow
}

# Verificar BD
$dbPath = "$env:USERPROFILE\.wheelsaver\top_repos.db"
if (Test-Path $dbPath) {
    $size = (Get-Item $dbPath).Length / 1MB
    Write-Host "  OK: BD encontrada en $dbPath ($([math]::Round($size, 1)) MB)" -ForegroundColor Green
} else {
    Write-Host "  INFO: BD aun no creada. Corre 'wheelsaver scrape' para inicializarla" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  WheelSaver instalado globalmente!"           -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Skills instalados en este proyecto:" -ForegroundColor Yellow
Write-Host "  wheelsaver       — CLI global desde cualquier carpeta" -ForegroundColor White
Write-Host "  wheel_saver      — Auditoria completa del proyecto" -ForegroundColor White
Write-Host "  wheel-ready      — Checklist de lo que le falta" -ForegroundColor White
Write-Host "  wheel-swap       — Busca alternativa a lo que codeas" -ForegroundColor White
Write-Host ""
Write-Host "Como usarlos:" -ForegroundColor Yellow
Write-Host "  wheelsaver search <keywords>   Buscar repos en la BD" -ForegroundColor Gray
Write-Host "  wheelsaver stats               Estadisticas de la BD" -ForegroundColor Gray
Write-Host "  wheelsaver scrape              Scrapear GitHub" -ForegroundColor Gray
Write-Host "  wheelsaver swap <feature>      Buscar alternativa" -ForegroundColor Gray
Write-Host "  wheelsaver ready               Checklist del proyecto" -ForegroundColor Gray
Write-Host ""
Write-Host "BD centralizada: $env:USERPROFILE\.wheelsaver\top_repos.db" -ForegroundColor DarkGray
