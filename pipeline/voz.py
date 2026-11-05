"""Narração com a voz clonada do JM + checagem de pronúncia + legendas reais.

Roda no ambiente de voz (GPU):
  .\\.venv-voz\\Scripts\\python.exe pipeline\\voz.py videos\\<slug>            # narra o que falta
  .\\.venv-voz\\Scripts\\python.exe pipeline\\voz.py videos\\<slug> --refazer b03 b05
  .\\.venv-voz\\Scripts\\python.exe pipeline\\voz.py videos\\<slug> --tudo     # refaz todos
  .\\.venv-voz\\Scripts\\python.exe pipeline\\voz.py teste "Uma frase qualquer"  # testa a voz

Para cada bloco:
  1. troca termos técnicos e números pela forma falada (canal/pronuncia.json + num2words);
  2. gera a fala com o Chatterbox Multilingual (PT) usando canal/voz/amostra.wav;
  3. transcreve com faster-whisper e compara com o roteiro — se ficou diferente, gera de novo;
  4. salva audio/<id>.wav e audio/<id>.json (palavras com tempo, para a legenda).
"""
from __future__ import annotations

import argparse
import difflib
import gc
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LIMIAR = 0.86  # semelhança mínima entre o que era pra falar e o que o Whisper ouviu
TENTATIVAS = 3


# ───────────────────────── texto ─────────────────────────
def carregar(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def para_fala(texto: str, dic: dict[str, str]) -> str:
    """Texto do roteiro -> texto que a voz deve pronunciar."""
    from num2words import num2words

    for termo in sorted((k for k in dic if not k.startswith("_")), key=len, reverse=True):
        texto = re.sub(rf"(?<![\w.]){re.escape(termo)}(?![\w])", dic[termo], texto)

    def numero(m: re.Match) -> str:
        bruto = m.group(0)
        n = bruto.replace(".", "").replace(",", ".")
        try:
            return num2words(float(n) if "." in n else int(n), lang="pt_BR")
        except Exception:
            return bruto

    texto = re.sub(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?", numero, texto)
    texto = texto.replace("/", " barra ").replace("%", " por cento")
    return re.sub(r"\s+", " ", texto).strip()


def normalizar(t: str) -> list[str]:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", t)


def semelhanca(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalizar(a), normalizar(b)).ratio()


# ───────────────────────── modelos ─────────────────────────
class Voz:
    def __init__(self, amostra: Path, cfg: dict):
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        self.torch = torch
        self.dev = "cuda" if torch.cuda.is_available() else "cpu"
        if self.dev == "cpu":
            print("⚠ GPU não encontrada — vai funcionar, mas bem devagar.")
        print(f"▶ carregando voz (Chatterbox Multilingual, {self.dev})…")
        self.m = ChatterboxMultilingualTTS.from_pretrained(device=self.dev)
        self.amostra = str(amostra)
        self.exag = cfg.get("expressividade", 0.5)
        self.cfg_w = cfg.get("cfgPeso", 0.5)
        self.temp = cfg.get("temperatura", 0.8)

    def falar(self, texto: str, destino: Path, semente: int) -> float:
        """Gera frase por frase (o modelo às vezes corta o fim de textos longos) e junta com pausas curtas."""
        import numpy as np
        import soundfile as sf

        self.torch.manual_seed(semente)
        if not getattr(self, "_preparado", False):
            self.m.prepare_conditionals(self.amostra, exaggeration=self.exag)
            self._preparado = True
        pausa = np.zeros(int(0.22 * self.m.sr), dtype=np.float32)
        pedacos = []
        for frase in dividir_frases(texto):
            wav = self.m.generate(frase, language_id="pt", exaggeration=self.exag, cfg_weight=self.cfg_w, temperature=self.temp)
            wav = aparar_silencio(wav, self.m.sr)
            if pedacos:
                pedacos.append(pausa)
            pedacos.append(wav.squeeze(0).detach().cpu().numpy().astype(np.float32))
        audio = np.concatenate(pedacos) if pedacos else pausa
        pico = float(np.max(np.abs(audio))) or 1.0
        audio = audio / max(pico, 1.0) * 0.98  # evita estourar ao converter para 16 bits
        sf.write(str(destino), audio, self.m.sr, subtype="PCM_16")  # WAV 16 bits: lido por qualquer ferramenta
        return len(audio) / self.m.sr

    def liberar(self):
        del self.m
        gc.collect()
        if self.dev == "cuda":
            self.torch.cuda.empty_cache()


def dividir_frases(texto: str) -> list[str]:
    """Quebra em frases; frases muito curtas (até 3 palavras) vão junto com a próxima."""
    partes = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", texto) if p.strip()]
    out: list[str] = []
    for p in partes:
        if out and len(out[-1].split()) <= 3:
            out[-1] = f"{out[-1]} {p}"
        else:
            out.append(p)
    return out or [texto]


def aparar_silencio(wav, sr, limiar=0.01, folga=0.08):
    """Corta silêncio do começo/fim, deixando uma pequena folga."""
    x = wav.abs().squeeze(0)
    idx = (x > limiar).nonzero()
    if len(idx) == 0:
        return wav
    a = max(0, int(idx[0]) - int(folga * sr))
    b = min(x.shape[0], int(idx[-1]) + int(folga * sr))
    return wav[..., a:b]


class Ouvido:
    def __init__(self, modelo: str = "large-v3"):
        import torch  # importar antes: no Windows isso expõe as DLLs de CUDA/cuDNN do PyTorch ao Whisper
        from faster_whisper import WhisperModel

        dev = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"▶ carregando Whisper ({modelo}, {dev})…")
        try:
            self.m = WhisperModel(modelo, device=dev, compute_type="float16" if dev == "cuda" else "int8")
        except Exception as e:  # cuDNN ausente etc.: cai para CPU com um modelo menor
            print(f"⚠ Whisper na GPU falhou ({e}); usando CPU com o modelo 'medium'.")
            self.m = WhisperModel("medium", device="cpu", compute_type="int8")

    def ouvir(self, wav: Path, dica: str = ""):
        # Carrega o áudio aqui (16 kHz mono) em vez de deixar o Whisper abrir o arquivo:
        # evita a incompatibilidade entre faster-whisper e versões novas do PyAV.
        import librosa
        import numpy as np

        audio, _ = librosa.load(str(wav), sr=16000, mono=True)
        # Sem "initial_prompt": passar o texto esperado fazia o Whisper pular trechos (e inflar a nota).
        segs, _ = self.m.transcribe(audio.astype(np.float32), language="pt", word_timestamps=True, vad_filter=False, condition_on_previous_text=False)
        palavras = [{"texto": w.word.strip(), "inicio": round(w.start, 3), "fim": round(w.end, 3)} for s in segs for w in (s.words or [])]
        return " ".join(p["texto"] for p in palavras), palavras


def alinhar_legenda(original: str, palavras_whisper: list[dict], duracao: float) -> list[dict]:
    """Legenda mostra o texto ORIGINAL do roteiro, com o tempo vindo do Whisper.

    Se o número de palavras bate, usa o tempo de cada uma; se não, distribui
    proporcionalmente ao tamanho das palavras entre o início e o fim da fala.
    """
    orig = re.findall(r"\S+", original)
    if palavras_whisper and len(palavras_whisper) == len(orig):
        return [{"texto": o, "inicio": w["inicio"], "fim": w["fim"]} for o, w in zip(orig, palavras_whisper)]
    ini = palavras_whisper[0]["inicio"] if palavras_whisper else 0.0
    fim = palavras_whisper[-1]["fim"] if palavras_whisper else duracao
    pesos = [len(o) + 2 for o in orig]
    total, t, out = sum(pesos), ini, []
    for o, p in zip(orig, pesos):
        d = (fim - ini) * p / total
        out.append({"texto": o, "inicio": round(t, 3), "fim": round(t + d, 3)})
        t += d
    return out


# ───────────────────────── fluxo ─────────────────────────
def narrar(pasta: Path, refazer: set[str] | None, tudo: bool):
    import soundfile as sf

    cfg = carregar(RAIZ / "canal" / "config.json")["voz"]
    dic = carregar(RAIZ / "canal" / "pronuncia.json")
    amostra = RAIZ / cfg["amostra"]
    if not amostra.exists():
        sys.exit(f"Amostra de voz não encontrada: {amostra}")
    rot = carregar(pasta / "roteiro.json")
    adir = pasta / "audio"
    adir.mkdir(exist_ok=True)

    for b in rot["blocos"]:
        b["_fala"] = para_fala(b["narracao"], dic)
    gerar = [b for b in rot["blocos"] if tudo or (refazer and b["id"] in refazer) or not wav_ok(adir / f"{b['id']}.wav")]
    # confere tudo que foi gerado agora + o que ainda não tem checagem salva
    pendentes = [b for b in rot["blocos"] if b in gerar or not (adir / f"{b['id']}.json").exists()]
    if not pendentes:
        print("✔ todos os blocos já têm narração conferida (use --refazer <id> ou --tudo).")
        return

    # 1) gerar as falas que faltam (modelo de voz na GPU)
    voz = Voz(amostra, cfg) if gerar else None
    for b in gerar:
        voz.falar(b["_fala"], adir / f"{b['id']}.wav", semente=1)
        (adir / f"{b['id']}.json").unlink(missing_ok=True)
        print(f"  ♪ {b['id']}")

    # 2) conferir (Whisper) — troca de modelo para não estourar os 8 GB da 4060
    #    Os blocos reprovados voltam para a voz com outra semente.
    for rodada in range(1, TENTATIVAS + 1):
        if rodada == 1 and voz is not None:
            voz.liberar()
        ouvido = Ouvido(cfg.get("whisper", "large-v3"))
        reprovados = []
        for b in pendentes:
            wav = adir / f"{b['id']}.wav"
            ouvido_txt, palavras = ouvido.ouvir(wav, b["_fala"])
            s = max(semelhanca(b["_fala"], ouvido_txt), semelhanca(b["narracao"], ouvido_txt))
            b["_nota"] = s
            dur = sf.info(str(wav)).duration
            (adir / f"{b['id']}.json").write_text(
                json.dumps({"semelhanca": round(s, 3), "ouvido": ouvido_txt, "palavras": alinhar_legenda(b["narracao"], palavras, dur)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if s < LIMIAR:
                reprovados.append(b)
                print(f"  ✗ {b['id']} {s:.0%}  ouviu: “{ouvido_txt}”")
            else:
                print(f"  ✓ {b['id']} {s:.0%}")
        del ouvido
        gc.collect()
        if not reprovados or rodada == TENTATIVAS:
            break
        print(f"▶ refazendo {len(reprovados)} bloco(s) (tentativa {rodada + 1}/{TENTATIVAS})…")
        voz = Voz(amostra, cfg)
        for b in reprovados:
            voz.falar(b["_fala"], adir / f"{b['id']}.wav", semente=rodada * 1000 + 7)
        voz.liberar()
        pendentes = reprovados

    ruins = [b["id"] for b in pendentes if b.get("_nota", 1) < LIMIAR]
    if ruins:
        print(f"⚠ ainda com pronúncia duvidosa: {', '.join(ruins)} — ouça e, se precisar, ajuste canal/pronuncia.json")
    print("✔ narração pronta. Próximo: python pipeline/fabrica.py tudo " + str(pasta.relative_to(RAIZ)))


def wav_ok(p: Path) -> bool:
    """Existe e está em PCM 16 bits (versões antigas salvavam em float e precisam ser refeitas)."""
    if not p.exists():
        return False
    try:
        import soundfile as sf

        return sf.info(str(p)).subtype == "PCM_16"
    except Exception:
        return False


def teste(frase: str):
    cfg = carregar(RAIZ / "canal" / "config.json")["voz"]
    dic = carregar(RAIZ / "canal" / "pronuncia.json")
    destino = RAIZ / "canal" / "voz" / "teste.wav"
    fala = para_fala(frase, dic)
    print(f"falando: {fala}")
    Voz(RAIZ / cfg["amostra"], cfg).falar(fala, destino, semente=1)
    print(f"✔ ouça: {destino}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta", help="videos/<slug>  ou  teste")
    ap.add_argument("frase", nargs="?", help="(com 'teste') frase para testar a voz")
    ap.add_argument("--refazer", nargs="*", default=None, help="ids dos blocos para refazer")
    ap.add_argument("--tudo", action="store_true")
    a = ap.parse_args()
    if a.pasta == "teste":
        teste(a.frase or "Olá! Esse é um teste da minha voz clonada para o canal.")
        return
    pasta = (RAIZ / a.pasta).resolve()
    narrar(pasta, set(a.refazer) if a.refazer else None, a.tudo)


if __name__ == "__main__":
    main()
