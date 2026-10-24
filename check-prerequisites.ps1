# ══════════════════════════════════════════════════════════════════════════════
# Script: Verificar Pre-requisitos
# ══════════════════════════════════════════════════════════════════════════════

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  VERIFICACIÓN DE PRE-REQUISITOS" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# ──────────────────────────────────────────────────────────────────────────────
# 1. Docker
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[1/3] Verificando Docker..." -ForegroundColor Yellow

try {
    $dockerVersion = docker --version 2>$null
    $dockerInPath = $true
} catch {
    $dockerInPath = $false
}

if (-not $dockerInPath -or -not $dockerVersion) {
    Write-Host "  ⚠️  Docker no encontrado en PATH" -ForegroundColor Yellow
    Write-Host "  🔍 Buscando en ubicaciones comunes..." -ForegroundColor Gray
    
    # Buscar Docker en ubicaciones comunes
    $dockerPaths = @(
        "C:\Program Files\Docker\Docker\resources\bin",
        "C:\ProgramData\DockerDesktop\version-bin",
        "$env:ProgramFiles\Docker\Docker\resources\bin",
        "$env:LOCALAPPDATA\Programs\Docker\Docker\resources\bin"
    )
    
    $dockerFound = $false
    foreach ($path in $dockerPaths) {
        if (Test-Path "$path\docker.exe") {
            Write-Host "  ✅ Docker encontrado en: $path" -ForegroundColor Green
            Write-Host "     (No está en PATH pero se puede configurar)" -ForegroundColor Gray
            $dockerFound = $true
            
            # Agregar temporalmente al PATH para verificar
            $env:PATH = "$path;$env:PATH"
            $dockerVersion = docker --version 2>$null
            break
        }
    }
    
    if (-not $dockerFound) {
        Write-Host "  ❌ Docker NO encontrado" -ForegroundColor Red
        Write-Host "     → Descarga: https://www.docker.com/products/docker-desktop/" -ForegroundColor Gray
        $allGood = $false
    } else {
        Write-Host ""
        Write-Host "  💡 Para configurar Docker en PATH ejecuta:" -ForegroundColor Cyan
        Write-Host "     .\setup-docker-path.ps1" -ForegroundColor White
    }
}

if ($dockerVersion) {
    Write-Host "  ✅ Docker instalado: $dockerVersion" -ForegroundColor Green
    
    # Verificar que esté corriendo
    $dockerPs = docker ps 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Docker está corriendo" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Docker instalado pero NO está corriendo" -ForegroundColor Yellow
        Write-Host "     → Abre Docker Desktop y espera a que inicie" -ForegroundColor Gray
        $allGood = $false
    }
}

Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# 2. Docker Compose
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[2/3] Verificando Docker Compose..." -ForegroundColor Yellow

try {
    $composeVersion = docker compose version 2>$null
    if ($composeVersion) {
        Write-Host "  ✅ Docker Compose disponible: $composeVersion" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Docker Compose NO encontrado" -ForegroundColor Yellow
        Write-Host "     → Actualiza Docker Desktop a la última versión" -ForegroundColor Gray
        $allGood = $false
    }
} catch {
    Write-Host "  ⚠️  Docker Compose NO encontrado" -ForegroundColor Yellow
    Write-Host "     → Actualiza Docker Desktop a la última versión" -ForegroundColor Gray
    $allGood = $false
}

Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# 3. Cloudflared
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[3/3] Verificando Cloudflared..." -ForegroundColor Yellow

try {
    $cloudflaredVersion = cloudflared --version 2>$null
    if ($cloudflaredVersion) {
        Write-Host "  ✅ Cloudflared instalado: $cloudflaredVersion" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Cloudflared NO encontrado" -ForegroundColor Red
        Write-Host "     → Instala con: choco install cloudflared" -ForegroundColor Gray
        Write-Host "     → O descarga: https://github.com/cloudflare/cloudflared/releases" -ForegroundColor Gray
        $allGood = $false
    }
} catch {
    Write-Host "  ❌ Cloudflared NO encontrado" -ForegroundColor Red
    Write-Host "     → Instala con: choco install cloudflared" -ForegroundColor Gray
    Write-Host "     → O descarga: https://github.com/cloudflare/cloudflared/releases" -ForegroundColor Gray
    $allGood = $false
}

Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# Resumen
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  RESUMEN" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

if ($allGood) {
    Write-Host "  🎉 TODO LISTO PARA COMENZAR" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Siguiente paso:" -ForegroundColor White
    Write-Host ""
    Write-Host "  1. Ejecuta el script automático:" -ForegroundColor White
    Write-Host "     powershell -ExecutionPolicy Bypass -File start-ollama-and-tunnel.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  O sigue las instrucciones manuales:" -ForegroundColor White
    Write-Host "     notepad INSTRUCCIONES-MANUAL.md" -ForegroundColor Cyan
} else {
    Write-Host "  ⚠️  FALTAN ALGUNOS PRE-REQUISITOS" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Revisa los errores arriba y:" -ForegroundColor White
    Write-Host "    1. Instala lo que falte" -ForegroundColor White
    Write-Host "    2. Ejecuta este script de nuevo" -ForegroundColor White
    Write-Host "    3. Cuando todo esté ✅, continúa con:" -ForegroundColor White
    Write-Host ""
    Write-Host "       powershell -ExecutionPolicy Bypass -File start-ollama-and-tunnel.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  O sigue las instrucciones manuales:" -ForegroundColor White
    Write-Host "     notepad INSTRUCCIONES-MANUAL.md" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
