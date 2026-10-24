# ══════════════════════════════════════════════════════════════════════════════
# Cloudflare Tunnel Starter para Ollama API
# ══════════════════════════════════════════════════════════════════════════════
# Este script inicia un túnel de Cloudflare para exponer el servicio Ollama
# que corre en Docker en el puerto 8081
# ══════════════════════════════════════════════════════════════════════════════

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Cloudflare Tunnel - Ollama API Bot Juridico" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que Docker esté corriendo
Write-Host "[1/4] Verificando servicios Docker..." -ForegroundColor Yellow
$dockerStatus = docker ps --filter "name=ollama" --format "{{.Names}}"
if ($dockerStatus -match "ollama") {
    Write-Host "  [OK] Ollama esta corriendo en Docker" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Ollama no esta corriendo" -ForegroundColor Red
    Write-Host "  Ejecuta: docker-compose -f docker-compose.ollama.yml up -d" -ForegroundColor Yellow
    exit 1
}

# Verificar que el puerto 8081 responda
Write-Host "[2/4] Verificando puerto 8081..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8081/v1/models" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  [OK] Nginx/Ollama responde correctamente" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] El puerto 8081 no responde aun" -ForegroundColor Yellow
    Write-Host "    Continuando de todas formas..." -ForegroundColor Gray
}

# Iniciar túnel de Cloudflare
Write-Host "[3/4] Iniciando túnel de Cloudflare..." -ForegroundColor Yellow
Write-Host "  Esto puede tomar 10-15 segundos..." -ForegroundColor Gray
Write-Host ""

# Crear un proceso en segundo plano y capturar la salida
$tunnelProcess = Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://localhost:8081" `
    -PassThru `
    -RedirectStandardOutput "tunnel-output.log" `
    -RedirectStandardError "tunnel-error.log" `
    -NoNewWindow

# Esperar a que el túnel se establezca
Start-Sleep -Seconds 8

# Leer la URL del log
$maxAttempts = 20
$attempt = 0
$tunnelUrl = $null

while ($attempt -lt $maxAttempts -and $null -eq $tunnelUrl) {
    Start-Sleep -Milliseconds 500
    if (Test-Path "tunnel-output.log") {
        $logContent = Get-Content "tunnel-output.log" -Raw
        if ($logContent -match "https://[a-z0-9-]+\.trycloudflare\.com") {
            $tunnelUrl = $matches[0]
            break
        }
    }
    $attempt++
}

Write-Host "[4/4] Resultado:" -ForegroundColor Yellow
Write-Host ""

if ($null -ne $tunnelUrl) {
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "  [SUCCESS] TUNEL CREADO EXITOSAMENTE" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  URL Pública: $tunnelUrl" -ForegroundColor Cyan
    Write-Host "  API Base URL: $tunnelUrl/v1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "SIGUIENTE PASO:" -ForegroundColor Yellow
    Write-Host "  1. Copia esta URL para actualizar en Railway:" -ForegroundColor White
    Write-Host "     $tunnelUrl/v1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  2. Actualiza la variable de entorno en Railway:" -ForegroundColor White
    Write-Host "     OLLAMA_BASE_URL=$tunnelUrl/v1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  3. Verifica que funcione:" -ForegroundColor White
    Write-Host "     curl $tunnelUrl/v1/models" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "IMPORTANTE:" -ForegroundColor Red
    Write-Host "  - Este tunel es TEMPORAL y se cerrara al cerrar esta ventana" -ForegroundColor Yellow
    Write-Host "  - Manten esta ventana abierta mientras uses el bot" -ForegroundColor Yellow
    Write-Host "  - Para produccion, considera usar un tunel con nombre" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Presiona Ctrl+C para detener el tunel..." -ForegroundColor Gray
    Write-Host ""
    
    # Mantener el script corriendo
    try {
        Wait-Process -Id $tunnelProcess.Id
    } catch {
        Write-Host "Tunel detenido." -ForegroundColor Yellow
    }
} else {
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "  [ERROR] No se pudo obtener la URL del tunel" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Revisa los logs:" -ForegroundColor Yellow
    Write-Host "  - tunnel-output.log" -ForegroundColor Gray
    Write-Host "  - tunnel-error.log" -ForegroundColor Gray
    Write-Host ""
    
    # Mostrar contenido de los logs si existen
    if (Test-Path "tunnel-output.log") {
        Write-Host "Output log:" -ForegroundColor Yellow
        Get-Content "tunnel-output.log" | Select-Object -Last 10
    }
    if (Test-Path "tunnel-error.log") {
        Write-Host "`nError log:" -ForegroundColor Yellow
        Get-Content "tunnel-error.log" | Select-Object -Last 10
    }
    
    Stop-Process -Id $tunnelProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
