# ══════════════════════════════════════════════════════════════════════════════
# Script: Levantar SOLO Ollama (sin túnel)
# ══════════════════════════════════════════════════════════════════════════════

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  INICIANDO OLLAMA LOCAL" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Cargar variables del .env
if (Test-Path ".env") {
    Write-Host "[INFO] Cargando configuración desde .env..." -ForegroundColor Yellow
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.+?)\s*$') {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            if ($name -match "OLLAMA") {
                Write-Host "  $name = $value" -ForegroundColor Gray
            }
        }
    }
    Write-Host ""
}

$OLLAMA_MODEL = $env:OLLAMA_MODEL
if (-not $OLLAMA_MODEL) { $OLLAMA_MODEL = "llama3.2:3b" }

$OLLAMA_VISION_MODEL = $env:OLLAMA_VISION_MODEL
if (-not $OLLAMA_VISION_MODEL) { $OLLAMA_VISION_MODEL = "llava:7b" }

Write-Host "Modelos a descargar:" -ForegroundColor Cyan
Write-Host "  • Texto:  $OLLAMA_MODEL" -ForegroundColor White
Write-Host "  • Visión: $OLLAMA_VISION_MODEL" -ForegroundColor White
Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# Verificar Docker
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[1/4] Verificando Docker..." -ForegroundColor Yellow

try {
    $dockerVersion = docker --version 2>$null
    if (-not $dockerVersion) {
        # Buscar Docker en ubicaciones comunes
        $dockerPaths = @(
            "C:\Program Files\Docker\Docker\resources\bin",
            "C:\ProgramData\DockerDesktop\version-bin"
        )
        
        foreach ($path in $dockerPaths) {
            if (Test-Path "$path\docker.exe") {
                $env:PATH = "$path;$env:PATH"
                break
            }
        }
    }
    
    $dockerVersion = docker --version 2>$null
    if ($dockerVersion) {
        Write-Host "  ✅ $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Docker no encontrado" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ❌ Docker no encontrado" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# Levantar contenedores
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[2/4] Levantando contenedores de Ollama..." -ForegroundColor Yellow
Write-Host "  Primera vez puede tomar 10-15 minutos descargando modelos..." -ForegroundColor Gray
Write-Host ""

docker compose -f docker-compose.ollama.yml up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Error levantando contenedores" -ForegroundColor Red
    exit 1
}

Write-Host "  ✅ Contenedores iniciados" -ForegroundColor Green
Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# Esperar a que estén listos
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[3/4] Esperando a que Ollama esté listo..." -ForegroundColor Yellow

$maxWait = 300  # 5 minutos
$waited = 0
$interval = 5

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds $interval
    $waited += $interval
    
    $healthStatus = docker inspect --format='{{.State.Health.Status}}' ollama-local 2>$null
    
    if ($healthStatus -eq "healthy") {
        Write-Host "  ✅ Ollama está listo!" -ForegroundColor Green
        break
    }
    
    Write-Host "  Esperando... $waited/${maxWait}s - Estado: $healthStatus" -ForegroundColor Gray
}

if ($waited -ge $maxWait) {
    Write-Host "  ⚠️  Timeout - revisa los logs: docker logs ollama-local" -ForegroundColor Yellow
}

Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# Verificar puerto
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "[4/4] Verificando puerto 8081..." -ForegroundColor Yellow

$maxAttempts = 10
$attempt = 0

while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8081/v1/models" -TimeoutSec 3 -ErrorAction Stop
        Write-Host "  ✅ Puerto 8081 responde correctamente" -ForegroundColor Green
        break
    } catch {
        $attempt++
        if ($attempt -lt $maxAttempts) {
            Write-Host "  Intento $attempt/$maxAttempts..." -ForegroundColor Gray
            Start-Sleep -Seconds 3
        }
    }
}

if ($attempt -ge $maxAttempts) {
    Write-Host "  ⚠️  Puerto no responde aún - puede estar descargando modelos" -ForegroundColor Yellow
    Write-Host "  Ver progreso: docker logs -f ollama-local" -ForegroundColor Cyan
}

Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# Resultado
# ──────────────────────────────────────────────────────────────────────────────
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  ✅ OLLAMA INICIADO" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Servicios corriendo:" -ForegroundColor Cyan
Write-Host "  • Ollama:  http://localhost:11435" -ForegroundColor White
Write-Host "  • Nginx:   http://localhost:8081" -ForegroundColor White
Write-Host ""
Write-Host "Modelos configurados:" -ForegroundColor Cyan
Write-Host "  • $OLLAMA_MODEL" -ForegroundColor White
Write-Host "  • $OLLAMA_VISION_MODEL" -ForegroundColor White
Write-Host ""
Write-Host "Verificar modelos descargados:" -ForegroundColor Yellow
Write-Host "  docker exec ollama-local ollama list" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ver logs de descarga:" -ForegroundColor Yellow
Write-Host "  docker logs -f ollama-local" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximo paso:" -ForegroundColor Yellow
Write-Host "  .\start-cloudflare-tunnel.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
