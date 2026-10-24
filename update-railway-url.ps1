# ══════════════════════════════════════════════════════════════════════════════
# Actualizar URL de Ollama en Railway
# ══════════════════════════════════════════════════════════════════════════════

param(
    [Parameter(Mandatory=$true)]
    [string]$CloudflareUrl
)

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Actualizador de URL Ollama para Railway" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Validar que la URL sea de Cloudflare
if ($CloudflareUrl -notmatch "https://.*\.trycloudflare\.com") {
    Write-Host "[ERROR] La URL debe ser de Cloudflare (*.trycloudflare.com)" -ForegroundColor Red
    Write-Host "Ejemplo: https://abc-def-ghi.trycloudflare.com" -ForegroundColor Yellow
    exit 1
}

# Agregar /v1 si no lo tiene
if ($CloudflareUrl -notmatch "/v1$") {
    $CloudflareUrl = "$CloudflareUrl/v1"
}

Write-Host "Nueva URL de Ollama: $CloudflareUrl" -ForegroundColor Green
Write-Host ""

# Actualizar .env local
Write-Host "[1/3] Actualizando .env local..." -ForegroundColor Yellow
$envFile = ".\.env"
if (Test-Path $envFile) {
    $content = Get-Content $envFile -Raw
    $content = $content -replace "OLLAMA_BASE_URL=.*", "OLLAMA_BASE_URL=$CloudflareUrl"
    Set-Content $envFile -Value $content -NoNewline
    Write-Host "  [OK] Archivo .env actualizado" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Archivo .env no encontrado" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/3] Comando para Railway CLI:" -ForegroundColor Yellow
Write-Host "  railway variables --set OLLAMA_BASE_URL=$CloudflareUrl" -ForegroundColor Cyan
Write-Host ""

Write-Host "[3/3] Pasos manuales en Railway Web:" -ForegroundColor Yellow
Write-Host "  1. Ve a: https://railway.app/" -ForegroundColor White
Write-Host "  2. Selecciona tu proyecto" -ForegroundColor White
Write-Host "  3. Ve a Variables > Add Variable" -ForegroundColor White
Write-Host "  4. Nombre: OLLAMA_BASE_URL" -ForegroundColor White
Write-Host "  5. Valor: $CloudflareUrl" -ForegroundColor Cyan
Write-Host "  6. Deploy automaticamente se activara" -ForegroundColor White
Write-Host ""

Write-Host "================================================================" -ForegroundColor Green
Write-Host "  [OK] Configuracion lista!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Prueba la URL:" -ForegroundColor Yellow
Write-Host "  curl $CloudflareUrl/models" -ForegroundColor Cyan
Write-Host ""
