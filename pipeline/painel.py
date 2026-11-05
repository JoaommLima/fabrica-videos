"""Painel de aprovação — abre no navegador, só no seu PC.

Uso:  python pipeline/painel.py          → http://127.0.0.1:8765

Para cada vídeo: assiste o longo e o short, escolhe a thumbnail e o título,
edita a descrição, vê as checagens automáticas e clica em Aprovar (com data de
publicação) ou Reprovar (com o motivo). A decisão fica em videos/<slug>/status.json,
que é o que a etapa de upload lê. Nada vai ao YouTube a partir daqui.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import mimetypes
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

RAIZ = Path(__file__).resolve().parent.parent
VIDEOS = RAIZ / "videos"
PORTA = 8765
DIAS = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6}


def lj(p: Path, padrao=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def cfg():
    return lj(RAIZ / "canal" / "config.json", {})


# ───────────────────────── checagens ─────────────────────────
_cache_lufs: dict[str, tuple[float, float | None]] = {}


def medir_lufs(video: Path) -> float | None:
    """Loudness integrado do arquivo final (ffmpeg ebur128). Fica em cache pelo mtime."""
    if not video.exists() or not shutil.which("ffmpeg"):
        return None
    chave, mt = str(video), video.stat().st_mtime
    if chave in _cache_lufs and _cache_lufs[chave][0] == mt:
        return _cache_lufs[chave][1]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", r.stderr)
    val = float(m[-1]) if m else None
    _cache_lufs[chave] = (mt, val)
    return val


def checagens(pasta: Path) -> list[tuple[str, str, str]]:
    """Lista de (nível, título, detalhe). nível: ok | aviso | erro."""
    c = cfg()
    out = []
    saida = pasta / "saida"
    rot = lj(pasta / "roteiro.json", {})
    blocos = rot.get("blocos", [])

    v = saida / "video.mp4"
    out.append(("ok", "Vídeo longo gerado", "") if v.exists() else ("erro", "Vídeo longo não encontrado", "rode produzir.ps1"))
    out.append(("ok", "Short gerado", "") if (saida / "short.mp4").exists() else ("aviso", "Short não gerado", "opcional"))

    sem_audio = [b["id"] for b in blocos if not (pasta / "audio" / f"{b['id']}.wav").exists()]
    if sem_audio:
        out.append(("erro", "Blocos sem narração", ", ".join(sem_audio)))
    notas = []
    for b in blocos:
        meta = lj(pasta / "audio" / f"{b['id']}.json")
        if meta:
            notas.append((b["id"], meta.get("semelhanca", 0), meta.get("ouvido", "")))
    ruins = [n for n in notas if n[1] < 0.86]
    if notas:
        if ruins:
            out.append(("aviso", f"Pronúncia duvidosa em {len(ruins)} bloco(s)", " · ".join(f"{i} ({s:.0%}): “{o[:60]}”" for i, s, o in ruins)))
        else:
            out.append(("ok", "Pronúncia conferida pelo Whisper", f"{len(notas)} blocos, menor nota {min(n[1] for n in notas):.0%}"))

    alvo = c.get("producao", {}).get("loudnessAlvoLUFS", -14)
    lufs = medir_lufs(v)
    if lufs is not None:
        nivel = "ok" if abs(lufs - alvo) <= 1.5 else "aviso"
        out.append((nivel, f"Volume {lufs:.1f} LUFS", f"alvo {alvo} LUFS"))

    fontes = pasta / "fontes.md"
    n_fontes = len(re.findall(r"https?://", fontes.read_text(encoding="utf-8"))) if fontes.exists() else 0
    out.append(("ok", f"{n_fontes} fonte(s) registrada(s)", "") if n_fontes else ("aviso", "Sem fontes registradas", "crie fontes.md com os links usados"))

    # roteiro repetido: compara palavras com os outros vídeos
    meu = set(re.findall(r"\w{5,}", " ".join(b["narracao"].lower() for b in blocos)))
    for outra in VIDEOS.iterdir():
        if outra == pasta or not (outra / "roteiro.json").exists() or not meu:
            continue
        dele = set(re.findall(r"\w{5,}", " ".join(b["narracao"].lower() for b in lj(outra / "roteiro.json", {}).get("blocos", []))))
        if dele and len(meu & dele) / len(meu | dele) > 0.45:
            out.append(("aviso", "Roteiro parecido com outro vídeo", outra.name))

    kit = lj(saida / "kit.json", {})
    for a in kit.get("avisos", []):
        out.append(("aviso", a, ""))
    thumbs = [saida / f"thumb-{i}.png" for i in (1, 2, 3)]
    out.append(("ok", "3 thumbnails", "") if all(t.exists() for t in thumbs) else ("aviso", "Thumbnails faltando", "python pipeline/fabrica.py thumbs …"))
    if c.get("publicacao", {}).get("marcarUsoDeIA"):
        out.append(("ok", "Aviso de voz sintética na descrição", "marque também “conteúdo alterado” no upload"))
    return out


# ───────────────────────── agenda ─────────────────────────
def proximo_horario() -> str:
    """Próximo dia/horário de postagem livre (pelos dias do config e vídeos já aprovados)."""
    pub = cfg().get("publicacao", {})
    dias = [DIAS[d] for d in pub.get("diasDePostagem", ["terca", "sexta"]) if d in DIAS]
    h, m = map(int, pub.get("horario", "18:00").split(":"))
    ocupados = {lj(p / "status.json", {}).get("publicarEm", "")[:16] for p in VIDEOS.iterdir() if (p / "status.json").exists()}
    d = dt.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
    for _ in range(120):
        d += dt.timedelta(days=1)
        if d.weekday() in dias and d.strftime("%Y-%m-%dT%H:%M") not in ocupados:
            return d.strftime("%Y-%m-%dT%H:%M")
    return d.strftime("%Y-%m-%dT%H:%M")


# ───────────────────────── HTML ─────────────────────────
CSS = """
:root{--bg:#161310;--bg2:#221d17;--card:#24201a;--line:#3a332a;--tx:#f3ece1;--sub:#a99c88;--amb:#ffae42;--ok:#7fc8c2;--err:#ff6a4d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.5 system-ui,Segoe UI,sans-serif}
a{color:var(--amb)}header{display:flex;align-items:center;gap:14px;padding:18px 28px;border-bottom:1px solid var(--line)}
header b{font-family:Consolas,monospace;letter-spacing:2px;color:var(--amb)}.faixa{height:8px;background:repeating-linear-gradient(-45deg,var(--amb) 0 10px,var(--bg) 10px 20px)}
main{max-width:1280px;margin:0 auto;padding:24px 28px 80px}h1{font-size:28px;margin:4px 0 18px}h2{font-size:15px;text-transform:uppercase;letter-spacing:2px;color:var(--sub);margin:28px 0 10px}
.grade{display:grid;grid-template-columns:2fr 1fr;gap:24px}@media(max-width:900px){.grade{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:16px}
video{width:100%;border-radius:4px;background:#000}.short video{max-height:520px;width:auto;display:block;margin:auto}
.thumbs{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.thumbs label{cursor:pointer;display:block;border:3px solid transparent;border-radius:6px;overflow:hidden;position:relative}
.thumbs input{position:absolute;opacity:0}.thumbs input:checked+img{outline:4px solid var(--amb);outline-offset:-4px}.thumbs img{width:100%;display:block}
.mini{display:flex;gap:10px;margin-top:8px;align-items:center;color:var(--sub);font-size:13px}.mini img{width:168px;border-radius:3px}
input[type=text],textarea,select,input[type=datetime-local]{width:100%;background:var(--bg2);color:var(--tx);border:1px solid var(--line);border-radius:4px;padding:10px;font:inherit}
textarea{min-height:260px;font-family:Consolas,monospace;font-size:14px}
.chk{list-style:none;padding:0;margin:0}.chk li{padding:8px 0;border-bottom:1px solid var(--line);display:flex;gap:10px}.chk small{color:var(--sub);display:block}
.ok::before{content:"✓";color:var(--ok);font-weight:700}.aviso::before{content:"!";color:var(--amb);font-weight:700}.erro::before{content:"✗";color:var(--err);font-weight:700}
.botoes{display:flex;gap:12px;margin-top:16px;flex-wrap:wrap}button{font:inherit;font-weight:700;border:0;border-radius:4px;padding:14px 26px;cursor:pointer}
.aprovar{background:var(--amb);color:#161310}.reprovar{background:transparent;color:var(--err);border:2px solid var(--err)}
.estado{display:inline-block;padding:3px 10px;border-radius:3px;font-size:13px;font-weight:700;font-family:Consolas,monospace}
.e-aprovado{background:var(--ok);color:#161310}.e-reprovado{background:var(--err);color:#161310}.e-pendente{background:var(--line);color:var(--tx)}.e-enviado{background:var(--amb);color:#161310}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid var(--line)}tr:hover td{background:var(--bg2)}
.msg{margin-top:14px;font-weight:700}
"""


def pagina(titulo: str, corpo: str) -> bytes:
    nome = html.escape(cfg().get("nomeCanal", "Canal"))
    return f"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)} · Painel</title><style>{CSS}</style></head><body><div class="faixa"></div>
<header><b>// {nome.upper()}</b><span style="color:var(--sub)">painel de aprovação</span><a href="/" style="margin-left:auto">todos os vídeos</a></header>
<main>{corpo}</main></body></html>""".encode("utf-8")


def estado_de(pasta: Path) -> str:
    return lj(pasta / "status.json", {}).get("estado", "pendente")


def lista() -> bytes:
    linhas = []
    for p in sorted(VIDEOS.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not (p / "roteiro.json").exists():
            continue
        rot = lj(p / "roteiro.json", {})
        st = lj(p / "status.json", {})
        e = st.get("estado", "pendente")
        quando = st.get("publicarEm", "").replace("T", " ") if e in ("aprovado", "enviado") else ""
        linhas.append(
            f'<tr><td><a href="/v/{p.name}">{html.escape(rot.get("titulo", p.name))}</a><br><small style="color:var(--sub)">{p.name}</small></td>'
            f'<td><span class="estado e-{e}">{e.upper()}</span></td><td>{quando}</td></tr>'
        )
    corpo = "<h1>Vídeos</h1><div class='card'><table><tr><th>Vídeo</th><th>Estado</th><th>Publicação</th></tr>" + "".join(linhas) + "</table></div>"
    return pagina("Vídeos", corpo)


def detalhe(slug: str) -> bytes:
    pasta = VIDEOS / slug
    rot = lj(pasta / "roteiro.json", {})
    kit = lj(pasta / "saida" / "kit.json", {})
    st = lj(pasta / "status.json", {})
    e = st.get("estado", "pendente")
    titulos = [kit.get("titulo", rot.get("titulo", ""))] + kit.get("titulosAlternativos", [])
    tit_atual = st.get("titulo", titulos[0])
    desc = st.get("descricao", kit.get("descricao", ""))
    tags = ", ".join(st.get("tags", kit.get("tags", [])))
    thumb_esc = st.get("thumb", 1)
    quando = st.get("publicarEm") or proximo_horario()
    arq = lambda n: f"/arquivo/{slug}/saida/{n}"
    ex = lambda n: (pasta / "saida" / n).exists()

    chk = "".join(f'<li class="{n}"><div>{html.escape(t)}<small>{html.escape(d)}</small></div></li>' for n, t, d in checagens(pasta))
    opcoes = "".join(f'<option {"selected" if t == tit_atual else ""}>{html.escape(t)}</option>' for t in dict.fromkeys(titulos + [tit_atual]))
    th = "".join(
        f'<label><input type="radio" name="thumb" value="{i}" {"checked" if i == thumb_esc else ""}><img src="{arq(f"thumb-{i}.png")}?t={int((pasta/"saida"/f"thumb-{i}.png").stat().st_mtime) if ex(f"thumb-{i}.png") else 0}"></label>'
        for i in (1, 2, 3)
    )
    mini = "".join(f'<img src="{arq(f"thumb-{i}.png")}">' for i in (1, 2, 3) if ex(f"thumb-{i}.png"))
    motivo_ant = f'<p style="color:var(--err)">Reprovado: {html.escape(st.get("motivo", ""))}</p>' if e == "reprovado" else ""

    corpo = f"""
<h1>{html.escape(rot.get("titulo", slug))} <span class="estado e-{e}">{e.upper()}</span></h1>{motivo_ant}
<div class="grade">
  <div class="card">{'<video controls preload="metadata" src="' + arq("video.mp4") + '"></video>' if ex("video.mp4") else "<p>Vídeo ainda não gerado.</p>"}</div>
  <div class="card short">{'<video controls preload="metadata" src="' + arq("short.mp4") + '"></video>' if ex("short.mp4") else "<p>Short ainda não gerado.</p>"}</div>
</div>
<h2>Thumbnail</h2>
<div class="thumbs">{th}</div>
<div class="mini">{mini}<span>← no tamanho que aparece no celular: dá pra ler?</span></div>
<div class="grade" style="margin-top:8px">
  <div>
    <h2>Título</h2><select id="titulo">{opcoes}</select>
    <input type="text" id="tituloLivre" placeholder="…ou escreva outro título" style="margin-top:8px">
    <h2>Descrição</h2><textarea id="descricao">{html.escape(desc)}</textarea>
    <h2>Tags</h2><input type="text" id="tags" value="{html.escape(tags)}">
    <h2>Comentário fixado</h2><input type="text" id="comentario" value="{html.escape(st.get("comentarioFixado", kit.get("comentarioFixado", "")))}">
  </div>
  <div>
    <h2>Checagens</h2><div class="card"><ul class="chk">{chk}</ul></div>
    <h2>Publicar em</h2><input type="datetime-local" id="quando" value="{quando}">
    <small style="color:var(--sub)">Vai como PRIVADO, agendado para essa data.</small>
    <div class="botoes"><button class="aprovar" onclick="decidir('aprovado')">Aprovar</button><button class="reprovar" onclick="decidir('reprovado')">Reprovar</button></div>
    <div class="msg" id="msg"></div>
  </div>
</div>
<script>
async function decidir(estado){{
  let motivo='';
  if(estado==='reprovado'){{motivo=prompt('O que precisa mudar?');if(motivo===null)return;}}
  const livre=document.getElementById('tituloLivre').value.trim();
  const corpo={{estado,motivo,
    titulo: livre||document.getElementById('titulo').value,
    descricao: document.getElementById('descricao').value,
    tags: document.getElementById('tags').value.split(',').map(s=>s.trim()).filter(Boolean),
    comentarioFixado: document.getElementById('comentario').value,
    thumb: Number((document.querySelector('input[name=thumb]:checked')||{{value:1}}).value),
    publicarEm: document.getElementById('quando').value}};
  if(corpo.titulo.length>100){{alert('Título com mais de 100 caracteres.');return;}}
  const r=await fetch('/api/{slug}/decisao',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(corpo)}});
  const m=document.getElementById('msg');
  if(r.ok){{m.textContent=estado==='aprovado'?'✓ Aprovado. A etapa de upload vai enviar como privado e agendado.':'Reprovado — motivo salvo.';setTimeout(()=>location.reload(),900);}}
  else m.textContent='Erro: '+await r.text();
}}
</script>"""
    return pagina(rot.get("titulo", slug), corpo)


# ───────────────────────── servidor ─────────────────────────
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _envia(self, cod: int, dados: bytes, tipo="text/html; charset=utf-8"):
        self.send_response(cod)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    def _slug_ok(self, slug: str) -> Path | None:
        p = (VIDEOS / slug).resolve()
        return p if p.parent == VIDEOS.resolve() and (p / "roteiro.json").exists() else None

    def do_GET(self):
        caminho = unquote(self.path.split("?")[0])
        if caminho == "/":
            return self._envia(200, lista())
        m = re.fullmatch(r"/v/([\w.-]+)", caminho)
        if m and self._slug_ok(m.group(1)):
            return self._envia(200, detalhe(m.group(1)))
        m = re.fullmatch(r"/arquivo/([\w.-]+)/(saida/[\w.-]+)", caminho)
        if m and self._slug_ok(m.group(1)):
            return self._arquivo((VIDEOS / m.group(1) / m.group(2)).resolve())
        self._envia(404, b"nao encontrado", "text/plain")

    def _arquivo(self, p: Path):
        if not p.exists() or VIDEOS.resolve() not in p.parents:
            return self._envia(404, b"nao encontrado", "text/plain")
        tam = p.stat().st_size
        tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        faixa = self.headers.get("Range")
        ini, fim = 0, tam - 1
        if faixa and (m := re.match(r"bytes=(\d*)-(\d*)", faixa)):
            if m.group(1):
                ini = int(m.group(1))
                fim = int(m.group(2)) if m.group(2) else tam - 1
            else:
                ini = tam - int(m.group(2))
            fim = min(fim, tam - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {ini}-{fim}/{tam}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(fim - ini + 1))
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(ini)
            resta = fim - ini + 1
            try:
                while resta > 0:
                    pedaco = f.read(min(1 << 20, resta))
                    if not pedaco:
                        break
                    self.wfile.write(pedaco)
                    resta -= len(pedaco)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                pass

    def do_POST(self):
        m = re.fullmatch(r"/api/([\w.-]+)/decisao", self.path)
        pasta = self._slug_ok(m.group(1)) if m else None
        if not pasta:
            return self._envia(404, b"nao encontrado", "text/plain")
        try:
            dados = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except json.JSONDecodeError:
            return self._envia(400, b"json invalido", "text/plain")
        if dados.get("estado") not in ("aprovado", "reprovado"):
            return self._envia(400, b"estado invalido", "text/plain")
        if dados["estado"] == "aprovado":
            erros = [t for n, t, _ in checagens(pasta) if n == "erro"]
            if erros:
                return self._envia(409, ("Não dá pra aprovar: " + "; ".join(erros)).encode("utf-8"), "text/plain; charset=utf-8")
        anterior = lj(pasta / "status.json", {})
        if anterior.get("estado") == "enviado":
            return self._envia(409, "Esse vídeo já foi enviado ao YouTube.".encode("utf-8"), "text/plain; charset=utf-8")
        dados["decididoEm"] = dt.datetime.now().isoformat(timespec="seconds")
        dados["historico"] = anterior.get("historico", []) + [{"estado": dados["estado"], "motivo": dados.get("motivo", ""), "em": dados["decididoEm"]}]
        (pasta / "status.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        self._envia(200, b"ok", "text/plain")


def main():
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else PORTA
    srv = ThreadingHTTPServer(("127.0.0.1", porta), H)
    url = f"http://127.0.0.1:{porta}"
    print(f"Painel aberto em {url}  (Ctrl+C para fechar)")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
