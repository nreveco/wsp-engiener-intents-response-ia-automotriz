# Abrir URL de Cloudflare en navegador para activar el túnel
$url = "https://politics-hourly-query-analysis.trycloudflare.com/v1/models"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Activacion de Tunel Cloudflare" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "URL del tunel: $url" -ForegroundColor Yellow
Write-Host ""
Write-Host "IMPORTANTE:" -ForegroundColor Red
Write-Host "  1. Se abrira tu navegador automaticamente" -ForegroundColor White
Write-Host "  2. Cloudflare puede pedir verificacion (captcha o espera)" -ForegroundColor White
Write-Host "  3. Una vez verificado, veras una respuesta JSON" -ForegroundColor White
Write-Host "  4. Despues de eso, la URL funcionara desde Railway" -ForegroundColor White
Write-Host ""
Write-Host "Abriendo navegador..." -ForegroundColor Green
Start-Sleep -Seconds 2

# Abrir en el navegador predeterminado
Start-Process $url

Write-Host ""
Write-Host "Navegador abierto!" -ForegroundColor Green
Write-Host ""
Write-Host "Esperando 10 segundos para que Cloudflare active el tunel..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "Probando la conexion desde PowerShell..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "  EXITO! El tunel esta funcionando" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Respuesta del servidor:" -ForegroundColor Cyan
    Write-Host $response.Content -ForegroundColor White
    Write-Host ""
    Write-Host "SIGUIENTE PASO:" -ForegroundColor Yellow
    Write-Host "  Actualiza esta URL en Railway:" -ForegroundColor White
    Write-Host "  https://politics-hourly-query-analysis.trycloudflare.com/v1" -ForegroundColor Cyan
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "  Todavia no funciona - Puede necesitar mas tiempo" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "POSIBLES CAUSAS:" -ForegroundColor Yellow
    Write-Host "  1. Cloudflare aun esta verificando tu navegador" -ForegroundColor White
    Write-Host "  2. El tunel se cerro - verifica que cloudflared este corriendo" -ForegroundColor White
    Write-Host "  3. Necesitas esperar unos segundos mas" -ForegroundColor White
    Write-Host ""
    Write-Host "INTENTA:" -ForegroundColor Yellow
    Write-Host "  - Verifica la pagina en el navegador que se abrio" -ForegroundColor White
    Write-Host "  - Espera 30 segundos y ejecuta este script de nuevo" -ForegroundColor White
    Write-Host "  - O prueba manualmente: curl $url" -ForegroundColor White
    Write-Host ""
}
