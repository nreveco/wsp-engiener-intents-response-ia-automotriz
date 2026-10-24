# ==============================================================================
# Script: Rebuild Ollama - Limpiar y levantar Ollama con tunel Cloudflare
# ==============================================================================

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  REBUILD OLLAMA + CLOUDFLARE TUNNEL" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Cargar variables del .env
if (Test-Path ".env") {
    Write-Host "[INFO] Cargando configuracion desde .env..." -ForegroundColor Yellow
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.+?)\s*$') {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$OLLAMA_MODEL = $env:OLLAMA_MODEL
if (-not $OLLAMA_MODEL) { $OLLAMA_MODEL = "llama3.2:3b" }

$OLLAMA_VISION_MODEL = $env:OLLAMA_VISION_MODEL
if (-not $OLLAMA_VISION_MODEL) { $OLLAMA_VISION_MODEL = "llava:7b" }

Write-Host "Modelos configurados:" -ForegroundColor Cyan
Write-Host "  Texto:  $OLLAMA_MODEL" -ForegroundColor White
Write-Host "  Vision: $OLLAMA_VISION_MODEL" -ForegroundColor White
Write-Host ""

# ------------------------------------------------------------------------------
# PASO 1: Detener y limpiar contenedores existentes
# ------------------------------------------------------------------------------
Write-Host "[1/6] Deteniendo contenedores existentes..." -ForegroundColor Yellow

docker compose -f docker-compose.ollama.yml down -v 2>$null
docker stop ollama-local ollama-nginx ollama-init 2>$null
docker rm ollama-local ollama-nginx ollama-init 2>$null

Write-Host "  Contenedores detenidos y eliminados" -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------------------
# PASO 2: Limpiar volumenes (opcional - mantener modelos descargados)
# ------------------------------------------------------------------------------
Write-Host "[2/6] Verificando volumenes..." -ForegroundColor Yellow

$cleanVolumes = Read-Host "Deseas limpiar volumenes? Esto eliminara los modelos descargados (s/N)"
if ($cleanVolumes -eq "s" -or $cleanVolumes -eq "S") {
    docker volume rm wsp-engiener-intents-response-ia_ollama_data 2>$null
    Write-Host "  Volumenes limpiados" -ForegroundColor Green
} else {
    Write-Host "  Volumenes preservados (modelos se mantienen)" -ForegroundColor Green
}
Write-Host ""

# ------------------------------------------------------------------------------
# PASO 3: Levantar Ollama
# ------------------------------------------------------------------------------
Write-Host "[3/6] Levantando Ollama..." -ForegroundColor Yellow
Write-Host "  Esto puede tomar varios minutos si es la primera vez..." -ForegroundColor Gray
Write-Host ""

docker compose -f docker-compose.ollama.yml up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "  Error levantando contenedores" -ForegroundColor Red
    exit 1
}

Write-Host "  Contenedores iniciados" -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------------------
# PASO 4: Esperar a que Ollama este listo
# ------------------------------------------------------------------------------
Write-Host "[4/6] Esperando a que Ollama este listo..." -ForegroundColor Yellow

$maxWait = 180  # 3 minutos
$waited = 0
$interval = 5

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds $interval
    $waited += $interval
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8081/v1/models" -TimeoutSec 3 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  Ollama esta listo!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "  Esperando... $waited/${maxWait}s" -ForegroundColor Gray
    }
}

if ($waited -ge $maxWait) {
    Write-Host "  Timeout - revisa los logs: docker logs ollama-local" -ForegroundColor Yellow
}

Write-Host ""

# ------------------------------------------------------------------------------
# PASO 5: Verificar modelos
# ------------------------------------------------------------------------------
Write-Host "[5/6] Verificando modelos instalados..." -ForegroundColor Yellow

try {
    $models = Invoke-RestMethod -Uri "http://localhost:8081/v1/models" -Method Get
    $modelNames = $models.data | ForEach-Object { $_.id }
    
    Write-Host "  Modelos disponibles:" -ForegroundColor Green
    foreach ($model in $modelNames) {
        Write-Host "    - $model" -ForegroundColor White
    }
} catch {
    Write-Host "  No se pudieron listar los modelos aun" -ForegroundColor Yellow
    Write-Host "  Los modelos se estan descargando en segundo plano" -ForegroundColor Gray
}

Write-Host ""

# ------------------------------------------------------------------------------
# PASO 6: Iniciar tunel de Cloudflare
# ------------------------------------------------------------------------------
Write-Host "[6/6] Iniciando tunel de Cloudflare..." -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  OLLAMA LISTO - INICIANDO TUNEL" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "El tunel se iniciara ahora. Copia la URL que aparezca y:" -ForegroundColor Yellow
Write-Host "1. Actualiza OLLAMA_BASE_URL en Railway con la nueva URL + /v1" -ForegroundColor White
Write-Host "2. Actualiza .env local con la misma URL" -ForegroundColor White
Write-Host "3. Mantén esta ventana abierta mientras el bot este funcionando" -ForegroundColor White
Write-Host ""
Write-Host "Presiona Ctrl+C para detener el tunel cuando termines" -ForegroundColor Gray
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Iniciar el tunel
cloudflared tunnel --url http://localhost:8081
