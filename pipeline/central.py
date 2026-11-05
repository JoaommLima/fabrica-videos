"""Central da Fábrica — interface gráfica no navegador (só no seu PC).

Abra com FABRICA.bat (ou: .venv\\Scripts\\python.exe pipeline\\central.py) → http://127.0.0.1:8765

Tudo vira botão: produzir vídeo, ouvir e refazer blocos da narração, comparar perfis de voz,
editar pronúncia, escolher estilo/música/volumes, revisar e aprovar. As ações rodam em segundo
plano e o log aparece ao vivo na tela.
"""
from __future__ import annotations

import datetime as dt
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from painel import checagens, lj, proximo_horario  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
VIDEOS = RAIZ / "videos"
PORTA = 8765
WIN = os.name == "nt"
PY_BASE = RAIZ / (".venv/Scripts/python.exe" if WIN else ".venv/bin/python")
PY_VOZ = RAIZ / (".venv-voz/Scripts/python.exe" if WIN else ".venv-voz/bin/python")
if not PY_BASE.exists():
    PY_BASE = Path(sys.executable)
if not PY_VOZ.exists():
    PY_VOZ = PY_BASE

# ───────────────────────── tarefas em segundo plano ─────────────────────────
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


class Tarefa:
    def __init__(self):
        self.trava = threading.Lock()
        self.titulo = ""
        self.linhas: list[str] = []
        self.rodando = False
        self.ok: bool | None = None
        self.inicio = 0.0
        self.fim = 0.0
        self.id = 0

    def estado(self) -> dict:
        with self.trava:
            return {
                "id": self.id,
                "titulo": self.titulo,
                "rodando": self.rodando,
                "ok": self.ok,
                "log": self.linhas[-400:],
                "segundos": int((self.fim or time.time()) - self.inicio) if self.inicio else 0,
            }

    def _add(self, txt: str):
        with self.trava:
            self.linhas.append(txt)
            if len(self.linhas) > 3000:
                self.linhas = self.linhas[-2000:]

    def iniciar(self, titulo: str, passos: list[tuple[str, list[str]]]) -> bool:
        with self.trava:
            if self.rodando:
                return False
            self.rodando, self.ok, self.titulo = True, None, titulo
            self.linhas, self.inicio, self.fim = [], time.time(), 0.0
            self.id += 1
        threading.Thread(target=self._rodar, args=(passos,), daemon=True).start()
        return True

    def _rodar(self, passos):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1", "FORCE_COLOR": "0"}
        ok = True
        for nome, cmd in passos:
            self._add(f"══ {nome} ══")
            try:
                p = subprocess.Popen(cmd, cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, bufsize=0)
                buf = b""
                while True:
                    ch = p.stdout.read(1)
                    if not ch:
                        break
                    if ch in (b"\n", b"\r"):
                        linha = ANSI.sub("", buf.decode("utf-8", "replace")).rstrip()
                        if linha:
                            if ch == b"\r":  # barra de progresso: substitui a última linha
                                with self.trava:
                                    if self.linhas and self.linhas[-1].startswith("⟳"):
                                        self.linhas[-1] = "⟳ " + linha
                                    else:
                                        self.linhas.append("⟳ " + linha)
                            else:
                                self._add(linha)
                        buf = b""
                    else:
                        buf += ch
                if buf.strip():
                    self._add(ANSI.sub("", buf.decode("utf-8", "replace")))
                if p.wait() != 0:
                    ok = False
                    self._add(f"✗ parou em: {nome} (código {p.returncode})")
                    break
            except Exception as e:  # noqa: BLE001
                ok = False
                self._add(f"✗ erro ao rodar {nome}: {e}")
                break
        with self.trava:
            self.rodando, self.ok, self.fim = False, ok, time.time()
        self._add("✔ concluído" if ok else "✗ terminou com erro — copie o log e mande para o Claude")


TAREFA = Tarefa()


def fab(*args: str) -> list[str]:
    return [str(PY_BASE), "pipeline/fabrica.py", *args]


def voz(*args: str) -> list[str]:
    return [str(PY_VOZ), "pipeline/voz.py", *args]


def passos_para(acao: str, slug: str | None, dados: dict) -> tuple[str, list] | None:
    v = f"videos/{slug}" if slug else ""
    if acao == "produzir":
        return "Produzir vídeo completo", [
            ("1/4 Narração com a sua voz", voz(v)),
            ("2/4 Vídeo longo + thumbnails + kit", fab("tudo", v)),
            ("3/4 Short: cenas", fab("renderizar", v, "--short")),
            ("4/4 Short: áudio", fab("mixar", v, "--short")),
        ]
    if acao == "narrar":
        return "Gerar narração", [("Narração", voz(v))]
    if acao == "refazer":
        ids = [i for i in dados.get("blocos", []) if re.fullmatch(r"[\w-]+", i)]
        if not ids:
            return None
        return f"Refazer blocos {', '.join(ids)}", [("Narração", voz(v, "--refazer", *ids))]
    if acao == "refazerTudo":
        return "Refazer toda a narração", [("Narração", voz(v, "--tudo"))]
    if acao == "longo":
        return "Vídeo longo", [("Vídeo longo + thumbnails + kit", fab("tudo", v))]
    if acao == "remixar":
        passos = []
        if (RAIZ / v / "saida" / "video-sem-audio.mp4").exists():
            passos.append(("Longo", fab("mixar", v)))
        if (RAIZ / v / "saida" / "short-sem-audio.mp4").exists():
            passos.append(("Short", fab("mixar", v, "--short")))
        return ("Remixar áudio (música/efeitos)", passos) if passos else None
    if acao == "short":
        return "Short", [("Cenas", fab("renderizar", v, "--short")), ("Áudio", fab("mixar", v, "--short"))]
    if acao == "thumbs":
        return "Thumbnails e kit", [("Thumbnails", fab("thumbs", v)), ("Kit", fab("kit", v))]
    if acao == "comparar":
        frase = (dados.get("frase") or "").strip()[:400]
        return "Comparar perfis de voz", [("Comparar", voz("comparar", *([frase] if frase else [])))]
    if acao == "testarVoz":
        frase = (dados.get("frase") or "").strip()[:400] or "Fala pessoal, hoje a gente vai entender o que é uma VLAN."
        return "Testar voz", [("Teste", voz("teste", frase))]
    if acao == "atualizar":
        return "Atualizar a fábrica (git pull)", [("git pull", ["git", "pull"])]
    return None


# ───────────────────────── dados para a tela ─────────────────────────
def cfg_canal() -> dict:
    return lj(RAIZ / "canal" / "config.json", {})


def salvar_json(p: Path, d) -> None:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def mtime(p: Path) -> int:
    return int(p.stat().st_mtime) if p.exists() else 0


def resumo_videos() -> list[dict]:
    out = []
    for p in sorted(VIDEOS.iterdir(), key=lambda x: mtime(x / "roteiro.json"), reverse=True):
        if not (p / "roteiro.json").exists():
            continue
        rot = lj(p / "roteiro.json", {})
        st = lj(p / "status.json", {})
        s = p / "saida"
        out.append({
            "slug": p.name,
            "titulo": rot.get("titulo", p.name),
            "estado": st.get("estado", "pendente"),
            "publicarEm": st.get("publicarEm", ""),
            "temVideo": (s / "video.mp4").exists(),
            "thumb": f"/arquivo/videos/{p.name}/saida/thumb-{st.get('thumb', 1)}.png?t={mtime(s / 'thumb-1.png')}" if (s / "thumb-1.png").exists() else "",
        })
    return out


def detalhe_video(slug: str) -> dict:
    p = VIDEOS / slug
    rot = lj(p / "roteiro.json", {})
    kit = lj(p / "saida" / "kit.json", {})
    st = lj(p / "status.json", {})
    s = p / "saida"
    blocos = []
    for b in rot.get("blocos", []):
        meta = lj(p / "audio" / f"{b['id']}.json", {}) or {}
        wav = p / "audio" / f"{b['id']}.wav"
        blocos.append({
            "id": b["id"],
            "cena": b["cena"]["tipo"],
            "narracao": b["narracao"],
            "nota": meta.get("semelhanca"),
            "ouvido": meta.get("ouvido", ""),
            "audio": f"/arquivo/videos/{slug}/audio/{b['id']}.wav?t={mtime(wav)}" if wav.exists() else "",
        })
    arq = lambda n: f"/arquivo/videos/{slug}/saida/{n}?t={mtime(s / n)}" if (s / n).exists() else ""
    titulos = [kit.get("titulo", rot.get("titulo", ""))] + kit.get("titulosAlternativos", [])
    return {
        "slug": slug,
        "titulo": rot.get("titulo", slug),
        "estado": st.get("estado", "pendente"),
        "motivo": st.get("motivo", ""),
        "video": arq("video.mp4"),
        "short": arq("short.mp4"),
        "thumbs": [arq(f"thumb-{i}.png") for i in (1, 2, 3)],
        "blocos": blocos,
        "checagens": [{"nivel": n, "titulo": t, "detalhe": d} for n, t, d in checagens(p)],
        "publicacao": {
            "titulos": list(dict.fromkeys(t for t in titulos + [st.get("titulo", "")] if t)),
            "titulo": st.get("titulo", titulos[0] if titulos else ""),
            "descricao": st.get("descricao", kit.get("descricao", "")),
            "tags": st.get("tags", kit.get("tags", [])),
            "comentarioFixado": st.get("comentarioFixado", kit.get("comentarioFixado", "")),
            "thumb": st.get("thumb", 1),
            "publicarEm": st.get("publicarEm") or proximo_horario(),
        },
    }


def dados_voz() -> dict:
    c = cfg_canal()
    pasta = RAIZ / "canal" / "voz"
    comparar = sorted(pasta.glob("comparar-*.wav")) if pasta.exists() else []
    teste = pasta / "teste.wav"
    perfis = {}
    try:
        src = (RAIZ / "pipeline" / "voz.py").read_text(encoding="utf-8")
        m = re.search(r"PERFIS = (\{.*?\n\})", src, re.S)
        import ast

        perfis = ast.literal_eval(m.group(1)) if m else {}
    except Exception:  # noqa: BLE001
        pass
    return {
        "config": c.get("voz", {}),
        "amostra": f"/arquivo/canal/voz/amostra.wav?t={mtime(pasta / 'amostra.wav')}" if (pasta / "amostra.wav").exists() else "",
        "teste": f"/arquivo/canal/voz/teste.wav?t={mtime(teste)}" if teste.exists() else "",
        "comparar": [{"nome": f.stem.replace("comparar-", ""), "url": f"/arquivo/canal/voz/{f.name}?t={mtime(f)}", "perfil": perfis.get(f.stem.replace("comparar-", ""), {})} for f in comparar],
    }


def dados_som() -> dict:
    c = cfg_canal()
    minhas = RAIZ / "canal" / "trilhas"
    lista = sorted(p for p in minhas.glob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"}) if minhas.exists() else []
    estilos = list(lj(RAIZ / "engine" / "src" / "estilos.json", {}).keys())
    return {
        "audio": c.get("audio", {}),
        "estilo": c.get("tema", {}).get("estilo", "bancada"),
        "estilos": estilos,
        "nomeCanal": c.get("nomeCanal", ""),
        "trilhas": [{"nome": p.name, "url": f"/arquivo/canal/trilhas/{p.name}"} for p in lista],
        "trilhaPadrao": "/arquivo/assets/trilhas/trilha-padrao.m4a",
    }


# ───────────────────────── arquivos que a tela pode abrir ─────────────────────────
PERMITIDOS = [
    re.compile(r"videos/[\w.-]+/saida/[\w.-]+\.(mp4|png|wav|txt|json)"),
    re.compile(r"videos/[\w.-]+/audio/[\w.-]+\.wav"),
    re.compile(r"canal/voz/[\w.-]+\.wav"),
    re.compile(r"canal/trilhas/[^/\\]+\.(mp3|wav|m4a|ogg)"),
    re.compile(r"assets/trilhas/[\w.-]+\.(m4a|mp3|wav)"),
]


def caminho_permitido(rel: str) -> Path | None:
    if ".." in rel or not any(r.fullmatch(rel) for r in PERMITIDOS):
        return None
    p = (RAIZ / rel).resolve()
    return p if p.is_file() and RAIZ.resolve() in p.parents else None


# ───────────────────────── servidor ─────────────────────────
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _envia(self, cod: int, dados, tipo="application/json; charset=utf-8"):
        if not isinstance(dados, (bytes, bytearray)):
            dados = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(cod)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    def _corpo(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(n) if n else b""

    def _slug(self, slug: str | None) -> str | None:
        if not slug or not re.fullmatch(r"[\w.-]+", slug):
            return None
        return slug if (VIDEOS / slug / "roteiro.json").exists() else None

    # ── GET
    def do_GET(self):
        u = urlparse(self.path)
        c = unquote(u.path)
        if c in ("/", "/index.html"):
            return self._envia(200, (Path(__file__).parent / "central.html").read_bytes(), "text/html; charset=utf-8")
        if c == "/api/videos":
            return self._envia(200, resumo_videos())
        if c.startswith("/api/video/"):
            s = self._slug(c.rsplit("/", 1)[-1])
            return self._envia(200, detalhe_video(s)) if s else self._envia(404, {"erro": "vídeo não encontrado"})
        if c == "/api/tarefa":
            return self._envia(200, TAREFA.estado())
        if c == "/api/voz":
            return self._envia(200, dados_voz())
        if c == "/api/pronuncia":
            return self._envia(200, lj(RAIZ / "canal" / "pronuncia.json", {}))
        if c == "/api/som":
            return self._envia(200, dados_som())
        if c.startswith("/arquivo/"):
            p = caminho_permitido(c[len("/arquivo/"):])
            return self._arquivo(p) if p else self._envia(404, {"erro": "arquivo não encontrado"})
        self._envia(404, {"erro": "rota não existe"})

    def _arquivo(self, p: Path):
        tam = p.stat().st_size
        tipo = mimetypes.guess_type(p.name)[0] or ("audio/mp4" if p.suffix == ".m4a" else "application/octet-stream")
        faixa = self.headers.get("Range")
        ini, fim = 0, tam - 1
        if faixa and (m := re.match(r"bytes=(\d*)-(\d*)", faixa)):
            if m.group(1):
                ini = int(m.group(1))
                fim = int(m.group(2)) if m.group(2) else tam - 1
            elif m.group(2):
                ini = max(0, tam - int(m.group(2)))
            fim = min(fim, tam - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {ini}-{fim}/{tam}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(fim - ini + 1))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            with open(p, "rb") as f:
                f.seek(ini)
                resta = fim - ini + 1
                while resta > 0 and (pedaco := f.read(min(1 << 20, resta))):
                    self.wfile.write(pedaco)
                    resta -= len(pedaco)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass

    # ── POST
    def do_POST(self):
        u = urlparse(self.path)
        c = unquote(u.path)
        if c == "/api/trilha":  # envio de música (corpo = arquivo)
            nome = os.path.basename(parse_qs(u.query).get("nome", [""])[0])
            if not re.fullmatch(r"[^/\\]{1,120}\.(mp3|wav|m4a|ogg)", nome, re.I):
                return self._envia(400, {"erro": "Use um arquivo .mp3, .wav, .m4a ou .ogg"})
            destino = RAIZ / "canal" / "trilhas"
            destino.mkdir(parents=True, exist_ok=True)
            (destino / nome).write_bytes(self._corpo())
            return self._envia(200, {"ok": True})
        try:
            dados = json.loads(self._corpo() or b"{}")
        except json.JSONDecodeError:
            return self._envia(400, {"erro": "dados inválidos"})

        if c == "/api/acao":
            acao = dados.get("acao", "")
            if acao == "abrirPasta":
                s = self._slug(dados.get("slug"))
                alvo = VIDEOS / s / "saida" if s else RAIZ
                alvo.mkdir(exist_ok=True)
                if WIN:
                    os.startfile(str(alvo))  # noqa: S606
                return self._envia(200, {"ok": True})
            slug = self._slug(dados.get("slug")) if dados.get("slug") else None
            if dados.get("slug") and not slug:
                return self._envia(404, {"erro": "vídeo não encontrado"})
            plano = passos_para(acao, slug, dados)
            if not plano:
                return self._envia(400, {"erro": "ação inválida"})
            if not TAREFA.iniciar(*plano):
                return self._envia(409, {"erro": "Já tem uma tarefa rodando. Espere terminar."})
            return self._envia(200, {"ok": True})

        if c.startswith("/api/decisao/"):
            s = self._slug(c.rsplit("/", 1)[-1])
            if not s:
                return self._envia(404, {"erro": "vídeo não encontrado"})
            pasta = VIDEOS / s
            if dados.get("estado") not in ("aprovado", "reprovado", "pendente"):
                return self._envia(400, {"erro": "estado inválido"})
            if dados["estado"] == "aprovado":
                erros = [t for n, t, _ in checagens(pasta) if n == "erro"]
                if erros:
                    return self._envia(409, {"erro": "Não dá pra aprovar: " + "; ".join(erros)})
            anterior = lj(pasta / "status.json", {})
            if anterior.get("estado") == "enviado":
                return self._envia(409, {"erro": "Esse vídeo já foi enviado ao YouTube."})
            dados["decididoEm"] = dt.datetime.now().isoformat(timespec="seconds")
            dados["historico"] = anterior.get("historico", []) + [{"estado": dados["estado"], "motivo": dados.get("motivo", ""), "em": dados["decididoEm"]}]
            salvar_json(pasta / "status.json", dados)
            return self._envia(200, {"ok": True})

        if c == "/api/config":
            conf = cfg_canal()
            if "voz" in dados:
                for k in ("expressividade", "cfgPeso", "temperatura"):
                    if k in dados["voz"]:
                        conf.setdefault("voz", {})[k] = round(min(1.0, max(0.0, float(dados["voz"][k]))), 2)
            if "audio" in dados:
                for k in ("volumeMusica", "volumeEfeitos"):
                    if k in dados["audio"]:
                        conf.setdefault("audio", {})[k] = round(min(1.0, max(0.0, float(dados["audio"][k]))), 2)
                if "trilha" in dados["audio"]:
                    conf.setdefault("audio", {})["trilha"] = str(dados["audio"]["trilha"])[:120]
            if "estilo" in dados and dados["estilo"] in lj(RAIZ / "engine" / "src" / "estilos.json", {}):
                conf.setdefault("tema", {})["estilo"] = dados["estilo"]
            if "nomeCanal" in dados and str(dados["nomeCanal"]).strip():
                nome = str(dados["nomeCanal"]).strip()[:40]
                conf["nomeCanal"] = nome
                conf.setdefault("tema", {})["nomeCanal"] = nome
            salvar_json(RAIZ / "canal" / "config.json", conf)
            return self._envia(200, {"ok": True})

        if c == "/api/pronuncia":
            if not isinstance(dados, dict):
                return self._envia(400, {"erro": "formato inválido"})
            limpo = {"_comentario": lj(RAIZ / "canal" / "pronuncia.json", {}).get("_comentario", "")}
            for k, v in dados.items():
                if k.startswith("_"):
                    continue
                k, v = str(k).strip()[:60], str(v).strip()[:120]
                if k and v:
                    limpo[k] = v
            salvar_json(RAIZ / "canal" / "pronuncia.json", limpo)
            return self._envia(200, {"ok": True})

        self._envia(404, {"erro": "rota não existe"})


def main():
    porta = next((int(a) for a in sys.argv[1:] if a.isdigit()), PORTA)
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", porta), H)
    except OSError:
        print(f"A Central já está aberta (porta {porta}). Abrindo no navegador…")
        webbrowser.open(f"http://127.0.0.1:{porta}")
        return
    url = f"http://127.0.0.1:{porta}"
    print(f"Central da Fábrica aberta em {url}\nDeixe esta janela aberta enquanto usa. Para fechar: Ctrl+C ou feche a janela.")
    if "--sem-navegador" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
