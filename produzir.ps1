# Produz um vídeo completo: voz clonada -> cenas -> mixagem -> thumbnails + kit (longo) e short
# Uso: powershell -ExecutionPolicy Bypass -File .\produzir.ps1 videos\demo-o-que-e-vlan
param([Parameter(Mandatory=$true)][string]$Pasta)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Rodar($titulo, $exe, [string[]]$argumentos) {
    Write-Host "== $titulo ==" -ForegroundColor Cyan
    & $exe @argumentos
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Parou em: $titulo (codigo $LASTEXITCODE). Copie as mensagens acima e mande para o Claude." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Rodar "1/4 Narrando com a sua voz" ".\.venv-voz\Scripts\python.exe" @("pipeline\voz.py", $Pasta)
Rodar "2/4 Video longo (16:9) + thumbnails + kit" ".\.venv\Scripts\python.exe" @("pipeline\fabrica.py", "tudo", $Pasta)
Rodar "3/4 Short (9:16): cenas" ".\.venv\Scripts\python.exe" @("pipeline\fabrica.py", "renderizar", $Pasta, "--short")
Rodar "4/4 Short (9:16): audio" ".\.venv\Scripts\python.exe" @("pipeline\fabrica.py", "mixar", $Pasta, "--short")

Write-Host ""
Write-Host "Pronto! Revise e aprove no painel: PAINEL.bat" -ForegroundColor Green
explorer.exe (Join-Path $PSScriptRoot "$Pasta\saida")
