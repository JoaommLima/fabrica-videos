# Instala a etapa de VOZ (voz clonada + checagem de pronúncia) — usa a placa NVIDIA.
# Uso: powershell -ExecutionPolicy Bypass -File .\instalar-voz.ps1
# Precisa de: Python 3.12 (o instalar.ps1 já instala) e driver NVIDIA atualizado.
# Ocupa ~8 GB (PyTorch + modelos, baixados na primeira execução).

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Achar-Python312 {
    $cands = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe"
    )
    foreach ($c in $cands) { if (Test-Path $c) { return $c } }
    try { $p = (& py -3.12 -c "import sys; print(sys.executable)" 2>$null); if ($LASTEXITCODE -eq 0 -and $p) { return $p.Trim() } } catch {}
    return $null
}

$py312 = Achar-Python312
if (-not $py312) {
    Write-Host "Python 3.12 nao encontrado. Instalando (nao mexe no Python que voce ja tem)..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
    $py312 = Achar-Python312
}
if (-not $py312) {
    Write-Host "Nao consegui instalar o Python 3.12 automaticamente." -ForegroundColor Red
    Write-Host "Baixe em https://www.python.org/downloads/release/python-3128/ (Windows installer 64-bit) e rode este instalador de novo."
    exit 1
}
Write-Host "Usando Python 3.12: $py312"

if (Test-Path .venv-voz) {
    if (-not (Test-Path .\.venv-voz\Scripts\python.exe)) { Remove-Item -Recurse -Force .venv-voz }
}
if (-not (Test-Path .venv-voz)) { & $py312 -m venv .venv-voz }
$py = ".\.venv-voz\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Falha ao criar o ambiente .venv-voz" -ForegroundColor Red; exit 1 }

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
