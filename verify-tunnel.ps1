# ==============================================================================
# Script: Verificar que el tunel de Cloudflare tenga ambos modelos
# ==============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$TunnelUrl
)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  VERIFICAR TUNEL Y MODELOS" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Si no se proporciona URL, pedir al usuario
if (-not $TunnelUrl) {
    Write-Host "Ingresa la URL del tunel de Cloudflare:" -ForegroundColor Yellow
    Write-Host "(Ejemplo: https://abc-xyz.trycloudflare.com)" -ForegroundColor Gray
    $TunnelUrl = Read-Host "URL"
}

# Limpiar URL (quitar /v1 si existe)
$TunnelUrl = $TunnelUrl.TrimEnd('/')
if ($TunnelUrl.EndsWith('/v1')) {
    $TunnelUrl = $TunnelUrl.Substring(0, $TunnelUrl.Length - 3)
}

Write-Host ""
Write-Host "[1/3] Verificando conexion al tunel..." -ForegroundColor Yellow
Write-Host "  URL: $TunnelUrl/v1/models" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri "$TunnelUrl/v1/models" -Method Get -TimeoutSec 10
    Write-Host "  Conexion exitosa!" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: No se puede conectar al tunel" -ForegroundColor Red
    Write-Host "  Asegurate de que cloudflared este corriendo" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Error: $_" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "[2/3] Verificando modelos disponibles..." -ForegroundColor Yellow

$models = $response.data | ForEach-Object { $_.id }

Write-Host "  Modelos encontrados:" -ForegroundColor White
foreach ($model in $models) {
    Write-Host "    - $model" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "[3/3] Validando modelos requeridos..." -ForegroundColor Yellow

$textModel = "llama3.2:3b"
$visionModel = "llava:7b"

$hasTextModel = $models -contains $textModel
$hasVisionModel = $models -contains $visionModel

if ($hasTextModel) {
    Write-Host "  $textModel (texto)" -ForegroundColor Green -NoNewline
    Write-Host " encontrado" -ForegroundColor White
} else {
    Write-Host "  $textModel (texto)" -ForegroundColor Red -NoNewline
    Write-Host " NO encontrado" -ForegroundColor White
}

if ($hasVisionModel) {
    Write-Host "  $visionModel (vision)" -ForegroundColor Green -NoNewline
    Write-Host " encontrado" -ForegroundColor White
} else {
    Write-Host "  $visionModel (vision)" -ForegroundColor Red -NoNewline
    Write-Host " NO encontrado" -ForegroundColor White
}

Write-Host ""

if ($hasTextModel -and $hasVisionModel) {
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "  TUNEL VALIDO - AMBOS MODELOS DISPONIBLES" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "URL para Railway:" -ForegroundColor Yellow
    Write-Host "  $TunnelUrl/v1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Copia esta URL y actualiza OLLAMA_BASE_URL en Railway" -ForegroundColor White
} else {
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "  ERROR - FALTAN MODELOS" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "El tunel no tiene todos los modelos necesarios." -ForegroundColor Yellow
    Write-Host "Ejecuta:" -ForegroundColor Yellow
    Write-Host "  .\rebuild-ollama.ps1" -ForegroundColor Cyan
    Write-Host ""
}
