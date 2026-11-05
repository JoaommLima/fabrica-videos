"""Gera os efeitos sonoros e a trilha padrão do canal — tudo sintetizado aqui, 100% original
(sem samples de terceiros, sem risco de direitos autorais).

  python pipeline/gerar_sons.py      (precisa de numpy; os arquivos já vêm prontos no repositório)

Saída:
  engine/public/sfx/*.wav            efeitos usados pelo motor de cenas
  assets/trilhas/trilha-padrao.m4a   música de fundo (loop) usada quando canal/trilhas/ está vazia
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
SR = 44100
rng = np.random.default_rng(7)


def t(seg: float) -> np.ndarray:
    return np.arange(int(seg * SR)) / SR


def env(n: int, ataque: float, queda: float) -> np.ndarray:
    a = max(1, int(ataque * SR))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[a:] = np.exp(-np.arange(n - a) / (queda * SR))
    return e


def passa_baixa(x: np.ndarray, corte: float | np.ndarray) -> np.ndarray:
    """Filtro de 1 polo (corte pode variar no tempo)."""
    corte = np.broadcast_to(corte, x.shape)
    a = 1 - np.exp(-2 * np.pi * corte / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def passa_alta(x: np.ndarray, corte: float) -> np.ndarray:
    return x - passa_baixa(x, corte)


def salvar(p: Path, x: np.ndarray, pico: float = 0.9) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    x = x / (np.max(np.abs(x)) or 1) * pico
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


# ───────────────────────── efeitos ─────────────────────────
def pop() -> np.ndarray:
    tt = t(0.12)
    f = 520 * np.exp(-tt * 18) + 260  # desce rápido, tipo "blup"
    fase = 2 * np.pi * np.cumsum(f) / SR
    corpo = np.sin(fase) * env(len(tt), 0.002, 0.035)
    clique = passa_alta(rng.normal(size=len(tt)), 2500) * env(len(tt), 0.0005, 0.004) * 0.25
    return corpo + clique


def whoosh(dur=0.45) -> np.ndarray:
    tt = t(dur)
    ruido = rng.normal(size=len(tt))
    forma = np.sin(np.pi * tt / dur) ** 2
    corte = 300 + 3500 * np.sin(np.pi * tt / dur) ** 1.5
    return passa_alta(passa_baixa(ruido, corte), 150) * forma


def tecla(varia: int) -> np.ndarray:
    tt = t(0.05)
    r = np.random.default_rng(100 + varia)
    clique = passa_alta(r.normal(size=len(tt)), 1800 + varia * 400) * env(len(tt), 0.0003, 0.006)
    tom = np.sin(2 * np.pi * (1900 + varia * 230) * tt) * env(len(tt), 0.0003, 0.004) * 0.3
    return clique + tom


def tick() -> np.ndarray:
    tt = t(0.04)
    return np.sin(2 * np.pi * 1600 * tt) * env(len(tt), 0.0005, 0.008)


def ding() -> np.ndarray:
    tt = t(1.0)
    parciais = [(1320, 1.0, 0.35), (1980, 0.5, 0.22), (2640, 0.25, 0.15), (3960, 0.12, 0.08)]
    return sum(a * np.sin(2 * np.pi * f * tt) * env(len(tt), 0.002, q) for f, a, q in parciais)


def clique_ui() -> np.ndarray:
    tt = t(0.07)
    return (np.sin(2 * np.pi * 880 * tt) * 0.6 + np.sin(2 * np.pi * 1320 * tt) * 0.4) * env(len(tt), 0.001, 0.015)


# ───────────────────────── trilha padrão ─────────────────────────
def nota(n: str) -> float:
    nomes = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    base, oit = n[:-1], int(n[-1])
    semi = nomes[base[0]] + (1 if "#" in base else 0)
    return 440 * 2 ** ((semi + (oit - 4) * 12) / 12)


def pad(freqs: list[float], dur: float) -> np.ndarray:
    tt = t(dur)
    x = np.zeros(len(tt))
    for f in freqs:
        for desafino in (-0.12, 0.0, 0.11):  # 3 osciladores levemente desafinados = som "largo"
            ff = f * 2 ** (desafino / 12)
            serra = 2 * ((ff * tt + rng.random()) % 1) - 1
            x += serra
    x = passa_baixa(x, 900 + 300 * np.sin(2 * np.pi * tt / dur))
    forma = np.minimum(1, tt / 0.8) * np.minimum(1, (dur - tt) / 0.8)
    return x * forma


def trilha(compassos: int = 4) -> np.ndarray:
    """Lo-fi calmo em Lá menor, ~72 BPM: Am7 · Fmaj7 · Cmaj7 · G6, com baixo, chimbal suave e chiado."""
    bpm = 72
    batida = 60 / bpm
    acorde_dur = batida * 4
    acordes = [
        (["A3", "C4", "E4", "G4"], "A2"),
        (["F3", "A3", "C4", "E4"], "F2"),
        (["C4", "E4", "G4", "B4"], "C3"),
        (["G3", "B3", "D4", "E4"], "G2"),
    ]
    partes = []
    for _ in range(compassos):
        for notas, baixo in acordes:
            p = pad([nota(n) for n in notas], acorde_dur) * 0.08
            tb = t(acorde_dur)
            b = np.sin(2 * np.pi * nota(baixo) * tb) * np.minimum(1, tb / 0.05) * np.exp(-tb / 2.2) * 0.35
            partes.append(p + b)
    musica = np.concatenate(partes)
    n = len(musica)
    # chimbal suave nos contratempos + "kick" macio no 1 e 3
    for k in range(int(n / SR / (batida / 2))):
        ini = int(k * batida / 2 * SR)
        if k % 2 == 1:
            h = passa_alta(rng.normal(size=int(0.05 * SR)), 6000) * env(int(0.05 * SR), 0.001, 0.012) * 0.05
            musica[ini : ini + len(h)] += h[: max(0, n - ini)]
        if k % 4 == 0:
            tk = t(0.25)
            kick = np.sin(2 * np.pi * (45 + 60 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 14) * 0.35
            musica[ini : ini + len(kick)] += kick[: max(0, n - ini)]
    chiado = passa_baixa(rng.normal(size=n), 4000) * 0.006
    return musica + chiado


def main():
    sfx = RAIZ / "engine" / "public" / "sfx"
    salvar(sfx / "pop.wav", pop(), 0.8)
    salvar(sfx / "whoosh.wav", whoosh(0.45), 0.6)
    salvar(sfx / "transicao.wav", whoosh(0.32), 0.45)
    for i in range(3):
        salvar(sfx / f"tecla{i + 1}.wav", tecla(i), 0.5)
    salvar(sfx / "tick.wav", tick(), 0.45)
    salvar(sfx / "ding.wav", ding(), 0.6)
    salvar(sfx / "clique.wav", clique_ui(), 0.6)
    wav = RAIZ / "assets" / "trilhas" / "trilha-padrao.wav"
    salvar(wav, trilha(4), 0.7)
    import subprocess

    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "160k", str(wav.with_suffix(".m4a"))], check=True)
    wav.unlink()
    print("✔ sons gerados")


if __name__ == "__main__":
    main()
