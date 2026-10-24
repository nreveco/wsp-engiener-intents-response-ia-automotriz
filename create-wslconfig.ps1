# ==============================================================================
# Script: Crear archivo .wslconfig para optimizar Docker Desktop
# ==============================================================================

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CREAR/ACTUALIZAR .wslconfig PARA DOCKER DESKTOP" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Detectar el directorio de usuario
$userProfile = $env:USERPROFILE
$wslConfigPath = Join-Path $userProfile ".wslconfig"

Write-Host "[1/4] Ubicacion del archivo: $wslConfigPath" -ForegroundColor Yellow
Write-Host ""

# Detectar recursos del sistema
$totalRAM = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB
$cpuCores = (Get-CimInstance Win32_Processor).NumberOfLogicalProcessors

$recommendedRAM = [math]::Min([math]::Floor($totalRAM * 0.7), 12)
$recommendedCPU = [math]::Min([math]::Floor($cpuCores * 0.75), 6)
$recommendedSwap = 2

Write-Host "[2/4] Configuracion recomendada:" -ForegroundColor Yellow
Write-Host "  RAM:  $recommendedRAM GB" -ForegroundColor Green
Write-Host "  CPUs: $recommendedCPU cores" -ForegroundColor Green
Write-Host "  SWAP: $recommendedSwap GB" -ForegroundColor Green
Write-Host ""

# Crear contenido del archivo
$wslConfigContent = @"
[wsl2]
# Memoria RAM asignada a WSL 2 (Docker Desktop)
memory=${recommendedRAM}GB

# Numero de procesadores logicos
processors=$recommendedCPU

# Espacio de swap
swap=${recommendedSwap}GB

# Localizacion del archivo de swap
# swapfile=%USERPROFILE%\AppData\Local\Temp\swap.vhdx
"@

# Verificar si el archivo ya existe
if (Test-Path $wslConfigPath) {
    Write-Host "[3/4] El archivo .wslconfig ya existe." -ForegroundColor Yellow
    Write-Host "  Creando backup en: $wslConfigPath.backup" -ForegroundColor Gray
    Copy-Item $wslConfigPath "$wslConfigPath.backup" -Force
    Write-Host "  Backup creado exitosamente" -ForegroundColor Green
} else {
    Write-Host "[3/4] El archivo .wslconfig no existe. Creando..." -ForegroundColor Yellow
}

# Escribir el archivo
try {
    $wslConfigContent | Out-File -FilePath $wslConfigPath -Encoding UTF8 -Force
    Write-Host "  Archivo .wslconfig creado/actualizado exitosamente!" -ForegroundColor Green
} catch {
    Write-Host "  Error al crear el archivo: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Mostrar contenido
Write-Host "[4/4] Contenido del archivo .wslconfig:" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan
Get-Content $wslConfigPath | ForEach-Object { Write-Host $_ -ForegroundColor White }
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Instrucciones finales
Write-Host "PROXIMOS PASOS:" -ForegroundColor Green
Write-Host ""
Write-Host "1. Reinicia WSL 2:" -ForegroundColor Yellow
Write-Host "   wsl --shutdown" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Cierra Docker Desktop completamente" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Vuelve a abrir Docker Desktop" -ForegroundColor Yellow
Write-Host ""
Write-Host "4. Reinicia los contenedores de Ollama:" -ForegroundColor Yellow
Write-Host "   cd d:\bot-jurico\wsp-engiener-intents-response-ia" -ForegroundColor Cyan
Write-Host "   docker compose -f docker-compose.ollama.yml down" -ForegroundColor Cyan
Write-Host "   docker compose -f docker-compose.ollama.yml up -d" -ForegroundColor Cyan
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  CONFIGURACION COMPLETADA" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
