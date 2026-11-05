# Instalador da Fábrica de vídeos (Windows 10/11)
# Uso: clique com o botão direito > "Executar com o PowerShell"
#   ou: powershell -ExecutionPolicy Bypass -File .\instalar.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Tem($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

Write-Host "== Fabrica de videos: instalacao ==" -ForegroundColor Cyan

if (-not (Tem node))    { Write-Host "Instalando Node.js LTS..."; winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements }
if (-not (Tem python))  { Write-Host "Instalando Python 3.12..."; winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements }
if (-not (Tem ffmpeg))  { Write-Host "Instalando ffmpeg...";     winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements }

# Atualiza o PATH desta janela depois do winget
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Instalando o motor de cenas (Remotion)..."
Push-Location engine
npm install
Pop-Location

Write-Host "Criando ambiente Python..."
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r pipeline\requirements.txt

Write-Host ""
Write-Host "Pronto! Teste com:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe pipeline\fabrica.py tudo videos\demo-o-que-e-vlan"
