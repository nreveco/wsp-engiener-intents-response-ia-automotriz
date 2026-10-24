# Quick Cloudflare Tunnel para Ollama
Write-Host "Iniciando tunel de Cloudflare..." -ForegroundColor Cyan
Write-Host "Puerto local: 8081 (Ollama via nginx)" -ForegroundColor Gray
Write-Host ""
Write-Host "La URL publica aparecera en unos segundos..." -ForegroundColor Yellow
Write-Host "Mantén esta ventana abierta!" -ForegroundColor Red
Write-Host ""
cloudflared tunnel --url http://localhost:8081
