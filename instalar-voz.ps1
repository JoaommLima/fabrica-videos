# Instala a etapa de VOZ (voz clonada + checagem de pronúncia) — usa a placa NVIDIA.
# Uso: powershell -ExecutionPolicy Bypass -File .\instalar-voz.ps1
# Precisa de: Python 3.12 (o instalar.ps1 já instala) e driver NVIDIA atualizado.
# Ocupa ~8 GB (PyTorch + modelos, baixados na primeira execução).

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv-voz)) { py -3.12 -m venv .venv-voz }
$py = ".\.venv-voz\Scripts\python.exe"

& $py -m pip install --upgrade pip
# PyTorch 2.6 com CUDA 12.4 (versão exigida pelo Chatterbox)
& $py -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
& $py -m pip install -r pipeline\requirements-voz.txt

Write-Host ""
Write-Host "Checando GPU..."
& $py -c "import torch; print('CUDA ok:', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'sem GPU')"

Write-Host ""
Write-Host "Pronto! Coloque sua amostra em canal\voz\amostra.wav e teste:" -ForegroundColor Green
Write-Host "  $py pipeline\voz.py teste `"Fala pessoal, hoje a gente vai entender o que é uma VLAN.`""
