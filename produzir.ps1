# Produz um vídeo completo: voz clonada -> cenas -> mixagem (longo + short)
# Uso: powershell -ExecutionPolicy Bypass -File .\produzir.ps1 videos\demo-o-que-e-vlan
param([Parameter(Mandatory=$true)][string]$Pasta)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "== 1/3 Narrando com a sua voz ==" -ForegroundColor Cyan
& .\.venv-voz\Scripts\python.exe pipeline\voz.py $Pasta

Write-Host "== 2/3 Video longo (16:9) ==" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe pipeline\fabrica.py tudo $Pasta

Write-Host "== 3/3 Short (9:16) ==" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe pipeline\fabrica.py renderizar $Pasta --short
& .\.venv\Scripts\python.exe pipeline\fabrica.py mixar $Pasta --short

Write-Host ""
Write-Host "Pronto! Arquivos em $Pasta\saida\ (video.mp4 e short.mp4)" -ForegroundColor Green
explorer.exe (Resolve-Path "$Pasta\saida")
