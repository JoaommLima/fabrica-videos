"""Integração com o servidor de casa (JmLab).

  python pipeline/jmlab.py enviar videos/<slug>   copia os arquivos finais para o NAS
  python pipeline/jmlab.py testar                 confere se a pasta do JmLab está acessível

Configuração em canal/config.json, bloco "jmlab":
  "ativo": true/false        liga ou desliga tudo
  "pasta": "\\\\jmlab\\arquivos\\fabrica"   pasta compartilhada no servidor
  "avisos": true/false       deixa bilhetes em <pasta>/_avisos para o servidor mandar no Telegram

O render continua no disco do PC (rápido). Aqui só copiamos o resultado.
Se o servidor estiver fora do ar, avisa e segue: o vídeo continua salvo no PC.
Nunca guarde token do Telegram aqui: quem manda a mensagem é o servidor.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import socket
import sys
from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parent.parent

# o que vai para o NAS (o resto de saida/ é intermediário)
FINAIS = ["video.mp4", "short.mp4", "thumb-1.png", "thumb-2.png", "thumb-3.png", "kit.json", "descricao.txt"]
EXTRAS = ["roteiro.json", "fontes.md", "status.json"]  # ficam na raiz de videos/<slug>/


def _lj(p: Path, padrao):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def config() -> dict:
    c = _lj(RAIZ / "canal" / "config.json", {}).get("jmlab", {}) or {}
    return {"ativo": bool(c.get("ativo", False)), "pasta": str(c.get("pasta", "")), "avisos": bool(c.get("avisos", True))}


def pasta_jmlab() -> Path | None:
    """Pasta do NAS se a integração está ligada e o servidor responde; senão None."""
    c = config()
    if not c["ativo"] or not c["pasta"]:
        return None
    p = Path(c["pasta"])
    try:
        return p if p.is_dir() else None
    except OSError:
        return None


def _copiar(origem: Path, destino: Path) -> bool:
    """Copia só se mudou. Grava em .parcial e renomeia: o Jellyfin nunca vê arquivo pela metade."""
    if destino.exists():
        a, b = origem.stat(), destino.stat()
        if a.st_size == b.st_size and int(a.st_mtime) <= int(b.st_mtime):
            return False
    tmp = destino.with_name(destino.name + ".parcial")
    shutil.copy2(origem, tmp)
    os.replace(tmp, destino)
    return True


def _nfo(rot: dict, kit: dict, st: dict, titulo_extra: str = "") -> str:
    """Ficha que o Jellyfin lê para mostrar título e descrição de verdade (a versão aprovada, se houver)."""
    titulo = (st.get("titulo") or kit.get("titulo") or rot.get("titulo") or "Vídeo") + titulo_extra
    plot = st.get("descricao") or kit.get("descricao") or rot.get("publicacao", {}).get("resumo", "")
    tags = "".join(f"  <tag>{escape(str(t))}</tag>\n" for t in kit.get("tags", [])[:15])
    return (
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n<movie>\n'
        f"  <title>{escape(titulo)}</title>\n  <plot>{escape(plot)}</plot>\n{tags}"
        "  <studio>Fábrica JM Lab</studio>\n</movie>\n"
    )


def enviar(pasta: Path) -> int:
    c = config()
    if not c["ativo"]:
        print("JmLab desligado em canal/config.json (jmlab.ativo = false). Nada a enviar.")
        return 0
    base = pasta_jmlab()
    if base is None:
        print(f"⚠ Não achei a pasta do JmLab ({c['pasta']}). O servidor está ligado e a pasta de rede conectada?")
        print("  O vídeo continua salvo no PC; dá para enviar depois pelo botão “Enviar para o JmLab”.")
        return 0  # não derruba a produção
    saida = pasta / "saida"
    if not (saida / "video.mp4").exists() and not (saida / "short.mp4").exists():
        print("Esse vídeo ainda não foi produzido: nada para enviar.")
        return 1
    destino = base / pasta.name
    destino.mkdir(parents=True, exist_ok=True)
    copiados = 0
    for nome in FINAIS:
        if (saida / nome).exists():
            print(f"@@progresso {FINAIS.index(nome) / len(FINAIS):.2f} copiando {nome}", flush=True)
            if _copiar(saida / nome, destino / nome):
                copiados += 1
                print(f"  ↑ {nome}")
    for nome in EXTRAS:
        if (pasta / nome).exists() and _copiar(pasta / nome, destino / nome):
            copiados += 1

    # Jellyfin: capa e fichas com o título do vídeo
    rot, kit, st = _lj(pasta / "roteiro.json", {}), _lj(saida / "kit.json", {}), _lj(pasta / "status.json", {})
    thumb = st.get("thumb", 1)
    capa = saida / f"thumb-{thumb}.png"
    if not capa.exists():
        capa = saida / "thumb-1.png"
    if capa.exists():
        for nome in ("poster.png", "video-thumb.png"):
            _copiar(capa, destino / nome)
    if (saida / "video.mp4").exists():
        (destino / "video.nfo").write_text(_nfo(rot, kit, st), encoding="utf-8")
    if (saida / "short.mp4").exists():
        (destino / "short.nfo").write_text(_nfo(rot, kit, st, " (short)"), encoding="utf-8")

    print(f"✔ {copiados} arquivo(s) novos em {destino}" if copiados else f"✔ JmLab já estava atualizado ({destino})")
    if os.environ.get("FABRICA_CENTRAL") != "1":  # pela linha de comando: avisa daqui mesmo
        aviso(True, "Enviado para o JmLab", pasta.name, rot.get("titulo", pasta.name))
    return 0


def aviso(ok: bool, tarefa: str, slug: str | None = None, video: str = "", segundos: int = 0,
          etapa: str = "", log: list[str] | None = None) -> bool:
    """Deixa um bilhete em <pasta>/_avisos. O servidor lê e manda no Telegram. Nunca levanta erro."""
    try:
        c = config()
        base = pasta_jmlab()
        if base is None or not c["avisos"]:
            return False
        d = base / "_avisos"
        d.mkdir(exist_ok=True)
        agora = dt.datetime.now()
        dados = {
            "versao": 1,
            "ok": bool(ok),
            "tarefa": tarefa[:120],
            "slug": slug or "",
            "video": (video or "")[:200],
            "segundos": int(segundos),
            "etapa": etapa[:120],
            "log": [str(x)[:300] for x in (log or [])][-12:],
            "pc": socket.gethostname()[:60],
            "em": agora.isoformat(timespec="seconds"),
        }
        nome = agora.strftime("%Y%m%d-%H%M%S-%f-") + re.sub(r"[^\w-]", "", slug or "fabrica")[:60] + ".json"
        tmp = d / (nome + ".parcial")
        tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, d / nome)
        return True
    except OSError:
        return False


def testar() -> int:
    c = config()
    print(f"ativo: {c['ativo']}  pasta: {c['pasta'] or '(vazia)'}  avisos: {c['avisos']}")
    base = pasta_jmlab()
    if base is None:
        print("✗ Pasta do JmLab inacessível (ou integração desligada).")
        return 1
    print(f"✔ Pasta acessível: {base}")
    if aviso(True, "Teste da Fábrica", None, "Se chegou no Telegram, está tudo ligado 🎉"):
        print("✔ Bilhete de teste deixado em _avisos — deve chegar no Telegram em até 1 minuto.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Integração Fábrica ↔ JmLab")
    ap.add_argument("etapa", choices=["enviar", "testar"])
    ap.add_argument("pasta", nargs="?")
    a = ap.parse_args()
    if a.etapa == "testar":
        return testar()
    if not a.pasta:
        ap.error("informe a pasta do vídeo, ex.: videos/demo-o-que-e-vlan")
    p = Path(a.pasta)
    p = p if p.is_absolute() else (RAIZ / p)
    return enviar(p.resolve())


if __name__ == "__main__":
    sys.exit(main())
