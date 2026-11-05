# Fábrica de vídeos — JM Lab

Pipeline próprio para produzir vídeos do canal (redes, homelab e tecnologia explicada) no Windows,
operado por conversa com o Claude Code. Inspirado no conceito do "Pipeline Canal Dark", mas feito do zero.

```
roteiro (Claude Code) → voz clonada (RTX 4060) → checagem de pronúncia (Whisper)
  → cenas animadas (Remotion) → montagem + volume -14 LUFS (ffmpeg)
  → shorts + thumbnails → painel de aprovação → YouTube (privado, agendado)
```

## Status

| Etapa | Status |
|---|---|
| Motor de cenas (9 tipos, longo 16:9 e short 9:16) | ✅ pronto |
| Preparar / renderizar / mixar (CLI) | ✅ pronto |
| Voz clonada local (Chatterbox Multilingual, RTX 4060) | ✅ pronto |
| Checagem de pronúncia + legendas reais (faster-whisper) | ✅ pronto |
| 4 estilos visuais + animação no ritmo da fala | ✅ pronto |
| 3 thumbnails + kit (título, descrição com capítulos, fontes, tags) | ✅ pronto |
| Shorts com cortes escolhidos (hoje: vídeo inteiro em 9:16) | ⏳ |
| Painel de aprovação no navegador (`PAINEL.bat`) | ✅ pronto |
| Upload pela YouTube Data API (privado + agendado) | ⏳ |
| Fila de temas | ⏳ |

## Instalação (Windows)

```powershell
git clone https://github.com/JoaommLima/fabrica-videos
cd fabrica-videos
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
```

## Uso

```powershell
# vídeo de demonstração (sem narração ainda: tempos estimados)
.\.venv\Scripts\python.exe pipeline\fabrica.py tudo videos\demo-o-que-e-vlan
.\.venv\Scripts\python.exe pipeline\fabrica.py tudo videos\demo-o-que-e-vlan --short

# pré-visualizar e ajustar cenas ao vivo no navegador
cd engine; npx remotion studio
```

Ou simplesmente abra a pasta no Claude Code e peça: *"faz um vídeo sobre DNS"* (veja `CLAUDE.md`).

## Tipos de cena

`abertura` · `lista` · `diagrama` (rede com ícones, VLANs coloridas e pacote viajando) · `terminal` (comandos digitando)
· `comparacao` · `numero` (contador) · `frase` · `linha-do-tempo` · `encerramento`

Formato completo em [`engine/src/types.ts`](engine/src/types.ts); exemplo em
[`videos/demo-o-que-e-vlan/roteiro.json`](videos/demo-o-que-e-vlan/roteiro.json).

## Licenças a observar
- **Remotion:** gratuito para pessoa física e empresas com até 3 funcionários.
- **Música:** use só trilhas com licença (ex.: Biblioteca de Áudio do YouTube) em `canal/trilhas/`.
- **YouTube:** marcar "conteúdo alterado/sintético" no upload quando usar voz clonada.
