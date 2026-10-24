# ══════════════════════════════════════════════════════════════════════════════
# Script: Verificar Estado de Ollama
# ══════════════════════════════════════════════════════════════════════════════

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  VERIFICANDO ESTADO - Ollama Local" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# 1. Verificar contenedores Docker
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[1/4] Verificando contenedores Docker..." -ForegroundColor Yellow
Write-Host ""

$containers = @("ollama-local", "ollama-nginx")
$allRunning = $true

foreach ($container in $containers) {
    $status = docker inspect --format='{{.State.Status}}' $container 2>$null
    $health = docker inspect --format='{{.State.Health.Status}}' $container 2>$null
    
    if ($status -eq "running") {
        $healthIcon = if ($health -eq "healthy") { "✅" } elseif ($health -eq "starting") { "🟡" } else { "❓" }
        Write-Host "  $healthIcon $container : $status ($health)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $container : NO CORRIENDO" -ForegroundColor Red
        $allRunning = $false
    }
}

Write-Host ""

if (-not $allRunning) {
    Write-Host "  [ERROR] Algunos contenedores no están corriendo" -ForegroundColor Red
    Write-Host "  Ejecuta: .\start-ollama-and-tunnel.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# ──────────────────────────────────────────────────────────────────────────────
# 2. Verificar modelos instalados
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[2/4] Verificando modelos instalados..." -ForegroundColor Yellow
Write-Host ""

try {
    $models = docker exec ollama-local ollama list 2>$null
    if ($models) {
        Write-Host $models
        Write-Host ""
    } else {
        Write-Host "  [WARN] No se pudieron listar modelos" -ForegroundColor Yellow
        Write-Host ""
    }
} catch {
    Write-Host "  [ERROR] Error al listar modelos" -ForegroundColor Red
    Write-Host ""
}

# ──────────────────────────────────────────────────────────────────────────────
# 3. Probar API local (puerto 8081)
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[3/4] Probando API local (http://localhost:8081)..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8081/v1/models" -TimeoutSec 5 -ErrorAction Stop
    $data = $response.Content | ConvertFrom-Json
    $modelCount = $data.data.Count
    Write-Host "  ✅ API responde - $modelCount modelo(s) disponible(s)" -ForegroundColor Green
    
    foreach ($model in $data.data) {
        Write-Host "     • $($model.id)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ❌ API no responde en puerto 8081" -ForegroundColor Red
    Write-Host "     Error: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# 4. Verificar túnel de Cloudflare
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[4/4] Verificando túnel de Cloudflare..." -ForegroundColor Yellow

$tunnelProcesses = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue

if ($tunnelProcesses) {
    Write-Host "  ✅ Túnel activo - $($tunnelProcesses.Count) proceso(s)" -ForegroundColor Green
    
    # Intentar leer la URL del log
    if (Test-Path "tunnel-output.log") {
        $logContent = Get-Content "tunnel-output.log" -Raw
        if ($logContent -match "https://[a-z0-9-]+\.trycloudflare\.com") {
            $tunnelUrl = $matches[0]
            Write-Host ""
            Write-Host "  📡 URL Pública: $tunnelUrl" -ForegroundColor Cyan
            Write-Host "  📡 API Endpoint: $tunnelUrl/v1" -ForegroundColor Cyan
            Write-Host ""
            
            # Probar túnel público
            Write-Host "     Probando túnel público..." -ForegroundColor Gray
            try {
                $response = Invoke-WebRequest -Uri "$tunnelUrl/v1/models" -TimeoutSec 10 -ErrorAction Stop
                Write-Host "     ✅ Túnel público funciona correctamente" -ForegroundColor Green
            } catch {
                Write-Host "     ⚠️  Túnel no responde (puede estar iniciándose)" -ForegroundColor Yellow
            }
        }
    }
} else {
    Write-Host "  ❌ No hay túnel activo" -ForegroundColor Red
    Write-Host "     Ejecuta: .\start-cloudflare-tunnel.ps1" -ForegroundColor Yellow
}

Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# Resumen
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  RESUMEN DE ESTADO" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$dockerOk = $allRunning
$tunnelOk = $null -ne $tunnelProcesses

Write-Host "  Docker Ollama:        $(if ($dockerOk) { '✅ OK' } else { '❌ ERROR' })" -ForegroundColor $(if ($dockerOk) { 'Green' } else { 'Red' })
Write-Host "  Cloudflare Tunnel:    $(if ($tunnelOk) { '✅ OK' } else { '❌ NO ACTIVO' })" -ForegroundColor $(if ($tunnelOk) { 'Green' } else { 'Yellow' })
Write-Host ""

if ($dockerOk -and $tunnelOk) {
    Write-Host "  🎉 TODO FUNCIONANDO CORRECTAMENTE" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Acciones disponibles:" -ForegroundColor White
    Write-Host "    • Ver logs de Ollama:  docker logs -f ollama-local" -ForegroundColor Gray
    Write-Host "    • Ver logs de túnel:   Get-Content tunnel-output.log -Wait" -ForegroundColor Gray
    Write-Host "    • Detener todo:        .\stop-ollama-and-tunnel.ps1" -ForegroundColor Gray
} elseif ($dockerOk -and -not $tunnelOk) {
    Write-Host "  ⚠️  Ollama funciona pero falta el túnel" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Ejecuta: .\start-cloudflare-tunnel.ps1" -ForegroundColor Cyan
} else {
    Write-Host "  ❌ Hay problemas - revisar arriba" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Ejecuta: .\start-ollama-and-tunnel.ps1" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
