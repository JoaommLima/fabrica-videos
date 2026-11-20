#!/usr/bin/env python3
"""JmLab: lê os bilhetes que a Fábrica deixa no NAS e manda no Telegram.

Roda no servidor pelo timer do systemd (a cada minuto).
  Bilhetes:  /srv/nas/arquivos/fabrica/_avisos/*.json
  Enviados:  /srv/nas/arquivos/fabrica/_avisos/enviados/  (apagados depois de 30 dias)
  Token:     /etc/jmlab/telegram.env  (TG_TOKEN e TG_CHAT, o mesmo do alerta SMART).
             O serviço roda como o usuário jm (não root); o systemd entrega o token
             por LoadCredential, sem precisar abrir a permissão do arquivo.

O bilhete é só dado: nada dele vira comando. Texto vai como texto puro (sem HTML/Markdown).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PASTA = Path(sys.argv[1] if len(sys.argv) > 1 else "/srv/nas/arquivos/fabrica/_avisos")
_cred = os.environ.get("CREDENTIALS_DIRECTORY")
ENV = Path(_cred) / "telegram" if _cred else Path("/etc/jmlab/telegram.env")
MAX_BYTES = 64 * 1024
GUARDAR_DIAS = 30


def ler_env() -> tuple[str, str]:
    vals = {}
    for linha in ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if "=" in linha and not linha.startswith("#"):
            k, v = linha.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals["TG_TOKEN"], vals["TG_CHAT"]


def _tempo(seg: int) -> str:
    m, s = divmod(max(0, int(seg)), 60)
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min" if h else (f"{m} min {s:02d} s" if m else f"{s} s")


def texto(d: dict) -> str:
    s = lambda k, n=200: str(d.get(k, ""))[:n]
    ok = bool(d.get("ok"))
    linhas = [("✅ " if ok else "❌ ") + "Fábrica · " + s("tarefa", 120)]
    if s("video"):
        linhas.append("🎬 " + s("video"))
    if d.get("segundos"):
        linhas.append("⏱ " + _tempo(d.get("segundos", 0)))
    if not ok:
        if s("etapa"):
            linhas.append("Parou em: " + s("etapa", 120))
        log = [str(x)[:200] for x in (d.get("log") or [])][-6:]
        if log:
            linhas.append("")
            linhas.extend(log)
    elif s("slug"):
        linhas.append("📂 \\\\jmlab\\arquivos\\fabrica\\" + s("slug", 80))
    if s("pc", 60):
        linhas.append("💻 " + s("pc", 60))
    return "\n".join(linhas)[:3500]


def enviar(token: str, chat: str, msg: str) -> None:
    corpo = urllib.parse.urlencode({"chat_id": chat, "text": msg, "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=corpo)
    with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 (URL fixa)
        if r.status != 200:
            raise RuntimeError(f"Telegram respondeu {r.status}")


def main() -> int:
    if not PASTA.is_dir():
        return 0
    feitos = PASTA / "enviados"
    feitos.mkdir(exist_ok=True)
    token, chat = ler_env()
    erro = 0
    for p in sorted(PASTA.glob("*.json"))[:20]:  # no máximo 20 por minuto
        if not p.is_file() or p.is_symlink():
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                raise ValueError("bilhete grande demais")
            d = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(d, dict):
                raise ValueError("formato inválido")
            msg = texto(d)
        except (OSError, ValueError) as e:
            msg = f"⚠️ Fábrica: bilhete ilegível ({p.name[:80]}): {e}"
        try:
            enviar(token, chat, msg)
        except Exception as e:  # noqa: BLE001 — tenta de novo no próximo minuto
            print(f"falha ao enviar {p.name}: {e}", file=sys.stderr)
            erro = 1
            break
        p.replace(feitos / p.name)
    limite = time.time() - GUARDAR_DIAS * 86400
    for p in feitos.glob("*.json"):
        try:
            if p.stat().st_mtime < limite:
                p.unlink()
        except OSError:
            pass
    return erro


if __name__ == "__main__":
    sys.exit(main())
