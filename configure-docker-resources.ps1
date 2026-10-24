# ==============================================================================
# Script: Configurar recursos de Docker Desktop
# ==============================================================================

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CONFIGURACION DE RECURSOS DE DOCKER DESKTOP" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------------------
# Verificar recursos del sistema
# ------------------------------------------------------------------------------
Write-Host "[1/3] Verificando recursos del sistema..." -ForegroundColor Yellow

$totalRAM = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB
$cpuCores = (Get-CimInstance Win32_Processor).NumberOfLogicalProcessors

Write-Host "  RAM Total:    $([math]::Round($totalRAM, 2)) GB" -ForegroundColor White
Write-Host "  CPU Cores:    $cpuCores" -ForegroundColor White
Write-Host ""

# ------------------------------------------------------------------------------
# Recomendar configuracion
# ------------------------------------------------------------------------------
Write-Host "[2/3] Configuracion recomendada para Ollama..." -ForegroundColor Yellow

$recommendedRAM = [math]::Min([math]::Floor($totalRAM * 0.7), 12)
$recommendedCPU = [math]::Min([math]::Floor($cpuCores * 0.75), 6)

Write-Host "  RAM recomendada:  $recommendedRAM GB (70`% del total)" -ForegroundColor Green
Write-Host "  CPUs recomendados: $recommendedCPU cores (75`% del total)" -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------------------------
# Instrucciones para configurar Docker Desktop
# ------------------------------------------------------------------------------
Write-Host "[3/3] Pasos para configurar Docker Desktop:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Abre Docker Desktop" -ForegroundColor White
Write-Host "2. Ve a Settings (⚙️) > Resources" -ForegroundColor White
Write-Host "3. Ajusta los valores:" -ForegroundColor White
Write-Host "   • Memory: $recommendedRAM GB" -ForegroundColor Cyan
Write-Host "   • CPUs: $recommendedCPU" -ForegroundColor Cyan
Write-Host "4. Haz clic en 'Apply & Restart'" -ForegroundColor White
Write-Host ""

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  NOTA: Después de aplicar, reinicia los contenedores" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Comandos para reiniciar:" -ForegroundColor Yellow
Write-Host "  docker compose -f docker-compose.ollama.yml down" -ForegroundColor Cyan
Write-Host "  docker compose -f docker-compose.ollama.yml up -d" -ForegroundColor Cyan
Write-Host ""
