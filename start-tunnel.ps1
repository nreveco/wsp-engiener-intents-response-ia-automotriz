# ==============================================================================
# Script: Start Cloudflare Tunnel (Ollama ya debe estar corriendo)
# ==============================================================================

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CLOUDFLARE TUNNEL PARA OLLAMA" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que Ollama este corriendo
Write-Host "[1/2] Verificando que Ollama este corriendo..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8081/v1/models" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  Ollama esta corriendo correctamente" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Ollama no esta corriendo en http://localhost:8081" -ForegroundColor Red
    Write-Host ""
    Write-Host "Ejecuta primero:" -ForegroundColor Yellow
    Write-Host "  .\rebuild-ollama.ps1" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host ""

# Iniciar tunel
Write-Host "[2/2] Iniciando tunel de Cloudflare..." -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  TUNEL INICIANDO" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Copia la URL que aparezca a continuacion y:" -ForegroundColor Yellow
Write-Host "1. Actualiza OLLAMA_BASE_URL en Railway: <URL>/v1" -ForegroundColor White
Write-Host "2. Actualiza .env local con la misma URL" -ForegroundColor White
Write-Host "3. Mantén esta ventana abierta" -ForegroundColor White
Write-Host ""
Write-Host "Presiona Ctrl+C para detener el tunel" -ForegroundColor Gray
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

cloudflared tunnel --url http://localhost:8081
