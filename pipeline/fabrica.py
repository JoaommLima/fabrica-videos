"""Fábrica de vídeos — linha de comando.

Uso (na raiz do projeto):
  python pipeline/fabrica.py preparar  videos/<slug>   # junta roteiro + tema + tempos -> props.json
  python pipeline/fabrica.py renderizar videos/<slug> [--short]
  python pipeline/fabrica.py mixar     videos/<slug>   # narração + trilha, volume padrão YouTube
  python pipeline/fabrica.py tudo      videos/<slug>

Estrutura de cada vídeo:
  videos/<slug>/roteiro.json        roteiro (blocos de narração + cena)
  videos/<slug>/audio/<id>.wav      narração de cada bloco (gerada pela etapa de voz)
  videos/<slug>/legendas.json       palavras com tempo (gerado pelo Whisper)
  videos/<slug>/saida/              arquivos finais
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENGINE = RAIZ / "engine"
FOLGA_BLOCO = 0.45  # respiro (s) entre um bloco e outro
PALAVRAS_POR_SEG = 2.6  # ritmo estimado de narração em PT-BR (só para rascunho sem áudio)


def carregar_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def salvar_json(p: Path, dados) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def duracao_wav(p: Path) -> float:
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg não encontrado. Rode o instalador (instalar.ps1) ou instale o ffmpeg e coloque no PATH.")
    return exe


# ───────────────────────── preparar ─────────────────────────
def preparar(pasta: Path) -> Path:
    cfg = carregar_json(RAIZ / "canal" / "config.json")
    rot = carregar_json(pasta / "roteiro.json")
    audio_dir = pasta / "audio"
    legendas_reais = pasta / "legendas.json"

    t = 0.0
    palavras_estimadas = []
    palavras_reais = []
    tem_audio = True
    for b in rot["blocos"]:
        wav = audio_dir / f"{b['id']}.wav"
        palavras = re.findall(r"\S+", b["narracao"])
        if wav.exists():
            fala = duracao_wav(wav)
            meta = audio_dir / f"{b['id']}.json"
            if meta.exists():  # tempos reais das palavras (gerados por pipeline/voz.py)
                for w in carregar_json(meta)["palavras"]:
                    palavras_reais.append({"texto": w["texto"], "inicio": round(t + w["inicio"], 3), "fim": round(t + w["fim"], 3)})
        else:
            tem_audio = False
            fala = max(2.5, len(palavras) / PALAVRAS_POR_SEG)
            # tempos aproximados só para pré-visualizar a legenda
            passo = fala / max(1, len(palavras))
            for i, w in enumerate(palavras):
                palavras_estimadas.append({"texto": w, "inicio": round(t + i * passo, 3), "fim": round(t + (i + 1) * passo, 3)})
        b["inicioAudio"] = round(t, 3)
        b["duracao"] = round(fala + FOLGA_BLOCO, 3)
        t += b["duracao"]

    props = {
        "titulo": rot["titulo"],
        "tema": cfg["tema"],
        "blocos": rot["blocos"],
        "mostrarLegenda": rot.get("mostrarLegenda", True),
        "legendas": carregar_json(legendas_reais) if legendas_reais.exists() else (palavras_reais if tem_audio else palavras_estimadas),
    }
    destino = pasta / "saida" / "props.json"
    salvar_json(destino, props)
    print(f"✔ props.json pronto: {len(rot['blocos'])} blocos, {t:.1f}s" + ("" if tem_audio else "  (RASCUNHO: tempos estimados, sem narração)"))
    return destino


# ───────────────────────── renderizar ─────────────────────────
def renderizar(pasta: Path, short: bool = False, chrome: str | None = None) -> Path:
    props = pasta / "saida" / "props.json"
    if not props.exists():
        preparar(pasta)
    saida = pasta / "saida" / ("short-sem-audio.mp4" if short else "video-sem-audio.mp4")
    npx = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [npx, "remotion", "render", "src/index.ts", "Short" if short else "Longo", str(saida), f"--props={props}", "--muted", "--log=error"]
    chrome = chrome or os.environ.get("REMOTION_CHROME")
    if chrome:
        cmd.append(f"--browser-executable={chrome}")
    print("▶ renderizando cenas…")
    subprocess.run(cmd, cwd=ENGINE, check=True)
    print(f"✔ {saida.relative_to(RAIZ)}")
    return saida


# ───────────────────────── mixar ─────────────────────────
def mixar(pasta: Path, short: bool = False) -> Path:
    cfg = carregar_json(RAIZ / "canal" / "config.json")
    props = carregar_json(pasta / "saida" / "props.json")
    video = pasta / "saida" / ("short-sem-audio.mp4" if short else "video-sem-audio.mp4")
    final = pasta / "saida" / ("short.mp4" if short else "video.mp4")
    lufs = cfg["producao"]["loudnessAlvoLUFS"]

    entradas, filtros, rotulos = ["-i", str(video)], [], []
    for i, b in enumerate(props["blocos"], start=1):
        wav = pasta / "audio" / f"{b['id']}.wav"
        if not wav.exists():
            continue
        entradas += ["-i", str(wav)]
        atraso = int(b["inicioAudio"] * 1000)
        filtros.append(f"[{len(rotulos) + 1}:a]adelay={atraso}|{atraso}[n{len(rotulos)}]")
        rotulos.append(f"[n{len(rotulos)}]")

    if not rotulos:
        print("⚠ sem narração em audio/ — copiando o vídeo mudo como está.")
        shutil.copy(video, final)
        return final

    trilha = next((p for p in (RAIZ / "canal" / "trilhas").glob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a"}), None) if (RAIZ / "canal" / "trilhas").exists() else None
    mix = f"{''.join(rotulos)}amix=inputs={len(rotulos)}:normalize=0[voz]"
    filtros.append(mix)
    if trilha:
        entradas += ["-stream_loop", "-1", "-i", str(trilha)]
        it = len(rotulos) + 1
        # trilha baixa e "abaixa" sozinha quando a voz entra (sidechain)
        filtros.append(f"[{it}:a]volume=0.18[tr]")
        filtros.append("[tr][voz]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[trd]")
        filtros.append("[voz][trd]amix=inputs=2:duration=first:normalize=0[mx]")
        ultimo = "[mx]"
    else:
        ultimo = "[voz]"
    filtros.append(f"{ultimo}loudnorm=I={lufs}:TP=-1.5:LRA=11[a]")

    cmd = [ffmpeg(), "-y", *entradas, "-filter_complex", ";".join(filtros), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"✔ {final.relative_to(RAIZ)}  (áudio normalizado em {lufs} LUFS)")
    return final


def main():
    ap = argparse.ArgumentParser(description="Fábrica de vídeos")
    ap.add_argument("etapa", choices=["preparar", "renderizar", "mixar", "tudo"])
    ap.add_argument("pasta", help="videos/<slug>")
    ap.add_argument("--short", action="store_true", help="formato vertical 9:16")
    ap.add_argument("--chrome", help="caminho de um Chrome/Chromium já instalado (opcional)")
    a = ap.parse_args()
    pasta = (RAIZ / a.pasta).resolve() if not Path(a.pasta).is_absolute() else Path(a.pasta)
    if not (pasta / "roteiro.json").exists():
        sys.exit(f"Não achei {pasta / 'roteiro.json'}")

    if a.etapa == "preparar":
        preparar(pasta)
    elif a.etapa == "renderizar":
        renderizar(pasta, a.short, a.chrome)
    elif a.etapa == "mixar":
        mixar(pasta, a.short)
    else:
        preparar(pasta)
        renderizar(pasta, a.short, a.chrome)
        mixar(pasta, a.short)


if __name__ == "__main__":
    main()
