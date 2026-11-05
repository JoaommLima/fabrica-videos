"""Fábrica de vídeos — linha de comando.

Uso (na raiz do projeto):
  python pipeline/fabrica.py preparar  videos/<slug>   # junta roteiro + tema + tempos -> props.json
  python pipeline/fabrica.py renderizar videos/<slug> [--short]
  python pipeline/fabrica.py mixar     videos/<slug>   # narração + trilha, volume padrão YouTube
  python pipeline/fabrica.py thumbs    videos/<slug>   # 3 opções de thumbnail
  python pipeline/fabrica.py kit       videos/<slug>   # título, descrição com capítulos, tags
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
import unicodedata
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
    """Duração de um WAV lendo o cabeçalho RIFF (aceita PCM 16/24 bits e float 32)."""
    import struct

    with open(p, "rb") as f:
        if f.read(4) != b"RIFF":
            raise ValueError(f"{p.name} não é WAV")
        f.read(4)
        if f.read(4) != b"WAVE":
            raise ValueError(f"{p.name} não é WAV")
        bytes_por_seg = None
        while True:
            cab = f.read(8)
            if len(cab) < 8:
                break
            nome, tam = cab[:4], struct.unpack("<I", cab[4:])[0]
            if nome == b"fmt ":
                fmt = f.read(tam)
                bytes_por_seg = struct.unpack("<I", fmt[8:12])[0]
            elif nome == b"data":
                if not bytes_por_seg:
                    break
                return tam / bytes_por_seg
            else:
                f.seek(tam + (tam & 1), 1)
    raise ValueError(f"Cabeçalho WAV inválido: {p}")


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg não encontrado. Rode o instalador (instalar.ps1) ou instale o ffmpeg e coloque no PATH.")
    return exe


# ───────────────────────── preparar ─────────────────────────
def montar_tema(cfg_tema: dict, estilo_roteiro: str | None = None) -> dict:
    """Preset do estilo (engine/src/estilos.json) + ajustes do canal."""
    presets = carregar_json(ENGINE / "src" / "estilos.json")
    estilo = estilo_roteiro or cfg_tema.get("estilo", "neon")
    if estilo not in presets:
        sys.exit(f"Estilo '{estilo}' não existe. Opções: {', '.join(presets)}")
    ajustes = {k: v for k, v in cfg_tema.items() if not k.startswith("_")}
    ajustes["estilo"] = estilo
    return {**presets[estilo], **ajustes}


def palavras_bloco(reais: list, estimadas: list, ini: float, dur: float) -> list:
    """Palavras (tempo absoluto) que caem dentro do bloco que começa em `ini`."""
    fonte = reais if reais else estimadas
    return [w for w in fonte if ini - 0.01 <= w["inicio"] < ini + dur]


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
        b["palavras"] = [{"texto": w["texto"], "inicio": round(w["inicio"] - t, 3), "fim": round(w["fim"] - t, 3)} for w in palavras_bloco(palavras_reais, palavras_estimadas, t, fala)]
        b["inicioAudio"] = round(t, 3)
        b["duracao"] = round(fala + FOLGA_BLOCO, 3)
        t += b["duracao"]

    props = {
        "titulo": rot["titulo"],
        "tema": montar_tema(cfg["tema"], rot.get("estilo")),
        "blocos": rot["blocos"],
        "mostrarLegenda": rot.get("mostrarLegenda", True),
        "legendas": carregar_json(legendas_reais) if legendas_reais.exists() else (palavras_reais if tem_audio else palavras_estimadas),
    }
    destino = pasta / "saida" / "props.json"
    salvar_json(destino, props)
    print(f"✔ props.json pronto: {len(rot['blocos'])} blocos, {t:.1f}s" + ("" if tem_audio else "  (RASCUNHO: tempos estimados, sem narração)"))
    return destino


# ───────────────────────── navegador do Remotion ─────────────────────────
_navegador_ok = False


def _versao_chrome_remotion() -> str:
    js = ENGINE / "node_modules" / "@remotion" / "renderer" / "dist" / "browser" / "BrowserFetcher.js"
    m = re.search(r"TESTED_VERSION = '([\d.]+)'", js.read_text(encoding="utf-8")) if js.exists() else None
    return m.group(1) if m else "133.0.6943.0"


def garantir_navegador() -> None:
    """O Remotion desenha as cenas num "Chrome Headless Shell" guardado em engine/node_modules/.remotion.
    O extrator de zip do próprio Remotion quebra em versões muito novas do Node (ex.: Node 26) e deixa
    só 2 arquivos extraídos. Aqui a fábrica baixa/extrai com o Python, no mesmo lugar que o Remotion procura."""
    global _navegador_ok
    if _navegador_ok:
        return
    import urllib.request
    import zipfile

    plat = "win64" if os.name == "nt" else "linux64"
    base = ENGINE / "node_modules" / ".remotion" / "chrome-headless-shell"
    destino = base / plat
    exe = destino / f"chrome-headless-shell-{plat}" / ("chrome-headless-shell.exe" if os.name == "nt" else "chrome-headless-shell")
    if exe.is_file():
        _navegador_ok = True
        return

    arquivo_zip = base / f"chrome-headless-shell-{plat}.zip"
    base.mkdir(parents=True, exist_ok=True)

    def extrair() -> bool:
        try:
            shutil.rmtree(destino, ignore_errors=True)
            with zipfile.ZipFile(arquivo_zip) as z:
                z.extractall(destino)
            if os.name != "nt":
                exe.chmod(0o755)
            return exe.is_file()
        except zipfile.BadZipFile:
            print("⚠ zip do navegador corrompido — baixando de novo…")
            arquivo_zip.unlink(missing_ok=True)
            return False

    if arquivo_zip.exists():
        print("▶ extraindo o navegador do Remotion…")
        if extrair():
            arquivo_zip.unlink(missing_ok=True)
            _navegador_ok = True
            return

    url = f"https://storage.googleapis.com/chrome-for-testing-public/{_versao_chrome_remotion()}/{plat}/chrome-headless-shell-{plat}.zip"
    print(f"▶ baixando o navegador do Remotion (~100 MB)…\n  {url}")
    try:
        tmp = arquivo_zip.with_suffix(".parcial")
        with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            feito = 0
            while bloco := r.read(1 << 20):
                f.write(bloco)
                feito += len(bloco)
                if total:
                    print(f"\r  {feito * 100 // total}%", end="", flush=True)
        print()
        tmp.replace(arquivo_zip)
        if extrair():
            arquivo_zip.unlink(missing_ok=True)
            _navegador_ok = True
            return
    except Exception as e:  # sem acesso direto: tenta o download do próprio Remotion
        print(f"⚠ download direto falhou ({e}); tentando pelo Remotion…")
        npx = "npx.cmd" if os.name == "nt" else "npx"
        subprocess.run([npx, "remotion", "browser", "ensure"], cwd=ENGINE, check=False)
        if exe.is_file() or (arquivo_zip.exists() and extrair()):
            _navegador_ok = True
            return

    sys.exit(
        "✗ Não consegui deixar o navegador do Remotion pronto.\n"
        f"  Confira a internet e se o antivírus não está bloqueando a pasta:\n  {base}"
    )


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
    else:
        garantir_navegador()
    print("▶ renderizando cenas…")
    subprocess.run(cmd, cwd=ENGINE, check=True)
    print(f"✔ {saida.relative_to(RAIZ)}")
    return saida


# ───────────────────────── mixar ─────────────────────────
def rodar_ffmpeg(args: list[str], etapa: str) -> None:
    r = subprocess.run([ffmpeg(), "-hide_banner", "-y", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"✗ ffmpeg falhou em: {etapa}")
        print("\n".join(r.stderr.strip().splitlines()[-25:]))
        sys.exit(1)


def montar_narracao(pasta: Path, blocos: list, destino: Path) -> bool:
    """Junta os WAVs dos blocos numa trilha só, cada um no seu tempo (biblioteca padrão, sem ffmpeg)."""
    SR = 24000
    total = int(sum(b["duracao"] for b in blocos) * SR) + SR
    buf = bytearray(total * 2)  # mono 16 bits, começa em silêncio
    algum = False
    tmp = destino.parent / "_conv.wav"
    for b in blocos:
        wav = pasta / "audio" / f"{b['id']}.wav"
        if not wav.exists():
            continue
        fonte = wav
        try:
            with wave.open(str(wav), "rb") as w:
                ok = (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, SR)
        except (wave.Error, EOFError):  # float 32, extensível etc.
            ok = False
        if not ok:  # formato diferente: converte para 24 kHz mono 16 bits
            rodar_ffmpeg(["-i", str(wav), "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(tmp)], f"converter {wav.name}")
            fonte = tmp
        with wave.open(str(fonte), "rb") as w:
            dados = w.readframes(w.getnframes())
        ini = int(b["inicioAudio"] * SR) * 2
        fim = min(len(buf), ini + len(dados))
        buf[ini:fim] = dados[: fim - ini]
        algum = True
    tmp.unlink(missing_ok=True)
    if algum:
        with wave.open(str(destino), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(bytes(buf))
    return algum


def mixar(pasta: Path, short: bool = False) -> Path:
    cfg = carregar_json(RAIZ / "canal" / "config.json")
    props = carregar_json(pasta / "saida" / "props.json")
    video = pasta / "saida" / ("short-sem-audio.mp4" if short else "video-sem-audio.mp4")
    final = pasta / "saida" / ("short.mp4" if short else "video.mp4")
    lufs = cfg["producao"]["loudnessAlvoLUFS"]

    narracao = pasta / "saida" / "narracao.wav"
    if not montar_narracao(pasta, props["blocos"], narracao):
        print("⚠ sem narração em audio/ — copiando o vídeo mudo como está.")
        shutil.copy(video, final)
        return final

    pasta_trilhas = RAIZ / "canal" / "trilhas"
    trilha = next((p for p in sorted(pasta_trilhas.glob("*")) if p.suffix.lower() in {".mp3", ".wav", ".m4a"}), None) if pasta_trilhas.exists() else None
    args = ["-i", str(video), "-i", str(narracao)]
    if trilha:
        # trilha baixa que "abaixa" sozinha quando a voz entra (sidechain)
        args += ["-stream_loop", "-1", "-i", str(trilha)]
        filtro = (
            "[1:a]asplit=2[voz][chave];"
            "[2:a]volume=0.18[tr];"
            "[tr][chave]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[trd];"
            f"[voz][trd]amix=inputs=2:duration=first:normalize=0,loudnorm=I={lufs}:TP=-1.5:LRA=11[a]"
        )
    else:
        filtro = f"[1:a]loudnorm=I={lufs}:TP=-1.5:LRA=11[a]"
    args += ["-filter_complex", filtro, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", str(final)]
    rodar_ffmpeg(args, "mixar áudio")
    print(f"✔ {final.relative_to(RAIZ)}  (áudio normalizado em {lufs} LUFS" + (f", trilha: {trilha.name})" if trilha else ")"))
    return final


# ───────────────────────── thumbnails ─────────────────────────
def thumbs(pasta: Path, chrome: str | None = None) -> list[Path]:
    cfg = carregar_json(RAIZ / "canal" / "config.json")
    rot = carregar_json(pasta / "roteiro.json")
    th = rot.get("publicacao", {}).get("thumbnail")
    if not th:
        abertura = next((b["cena"] for b in rot["blocos"] if b["cena"]["tipo"] == "abertura"), {})
        th = {"texto": abertura.get("titulo", rot["titulo"]), "selo": abertura.get("selo")}
    tema = montar_tema(cfg["tema"], rot.get("estilo"))
    npx = "npx.cmd" if os.name == "nt" else "npx"
    chrome = chrome or os.environ.get("REMOTION_CHROME")
    if not chrome:
        garantir_navegador()
    saidas = []
    for v in (1, 2, 3):
        props = pasta / "saida" / f"thumb-{v}.props.json"
        salvar_json(props, {**th, "tema": tema, "variante": v})
        destino = pasta / "saida" / f"thumb-{v}.png"
        cmd = [npx, "remotion", "still", "src/index.ts", "Thumb", str(destino), f"--props={props}", "--log=error"]
        if chrome:
            cmd.append(f"--browser-executable={chrome}")
        subprocess.run(cmd, cwd=ENGINE, check=True)
        saidas.append(destino)
    print(f"✔ 3 thumbnails em {(pasta / 'saida').relative_to(RAIZ)}")
    return saidas


# ───────────────────────── kit de publicação ─────────────────────────
def _tempo(seg: float) -> str:
    s = int(seg)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def kit(pasta: Path) -> Path:
    """Título, descrição com capítulos e fontes, tags e comentário fixado."""
    cfg = carregar_json(RAIZ / "canal" / "config.json")
    rot = carregar_json(pasta / "roteiro.json")
    props_p = pasta / "saida" / "props.json"
    if not props_p.exists():
        preparar(pasta)
    blocos = carregar_json(props_p)["blocos"]
    pub = rot.get("publicacao", {})

    # capítulos: cada cena com título vira capítulo; o YouTube exige 1º em 0:00, mínimo 3, cada um com 10 s+
    caps: list[list] = []
    for b in blocos:
        c = b["cena"]
        nome = "Introdução" if c["tipo"] == "abertura" else c.get("titulo")
        if not nome:
            continue
        if c["tipo"] == "encerramento":
            nome = "Encerramento"
        if caps and b["inicioAudio"] - caps[-1][0] < 10:
            continue  # muito perto do anterior: junta
        caps.append([b["inicioAudio"] if caps else 0.0, nome])
    caps_txt = "\n".join(f"{_tempo(t)} {n}" for t, n in caps) if len(caps) >= 3 else ""

    fontes = []
    fp = pasta / "fontes.md"
    if fp.exists():
        fontes = re.findall(r"https?://\S+", fp.read_text(encoding="utf-8"))

    tags = pub.get("tags", [])
    partes = [pub.get("resumo", rot["titulo"])]
    if caps_txt:
        partes.append("⏱ Capítulos\n" + caps_txt)
    if fontes:
        partes.append("📚 Fontes\n" + "\n".join(fontes))
    if cfg["publicacao"].get("marcarUsoDeIA"):
        partes.append("ℹ️ A narração deste vídeo usa uma versão sintética da voz do próprio autor. Roteiro e revisão: " + cfg["nomeCanal"] + ".")
    sem_acento = lambda x: "".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c))
    partes.append(" ".join("#" + re.sub(r"\W", "", sem_acento(t).title()) for t in tags[:3]))
    descricao = "\n\n".join(partes)

    titulos = pub.get("titulos", [rot["titulo"]])
    dados = {
        "titulo": titulos[0],
        "titulosAlternativos": titulos[1:],
        "descricao": descricao,
        "tags": tags,
        "comentarioFixado": pub.get("comentarioFixado", ""),
        "categoria": cfg["publicacao"]["categoriaYoutube"],
        "avisos": [],
    }
    if len(titulos[0]) > 100:
        dados["avisos"].append("Título passa de 100 caracteres (limite do YouTube).")
    if len(descricao) > 5000:
        dados["avisos"].append("Descrição passa de 5000 caracteres.")
    if len(", ".join(tags)) > 500:
        dados["avisos"].append("Tags passam de 500 caracteres.")
    destino = pasta / "saida" / "kit.json"
    salvar_json(destino, dados)
    (pasta / "saida" / "descricao.txt").write_text(descricao, encoding="utf-8")
    print(f"✔ kit de publicação: {destino.relative_to(RAIZ)}")
    return destino


def main():
    ap = argparse.ArgumentParser(description="Fábrica de vídeos")
    ap.add_argument("etapa", choices=["preparar", "renderizar", "mixar", "thumbs", "kit", "tudo"])
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
    elif a.etapa == "thumbs":
        thumbs(pasta, a.chrome)
    elif a.etapa == "kit":
        kit(pasta)
    else:
        preparar(pasta)
        renderizar(pasta, a.short, a.chrome)
        mixar(pasta, a.short)
        if not a.short:
            thumbs(pasta, a.chrome)
            kit(pasta)


if __name__ == "__main__":
    main()
