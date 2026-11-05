# Fábrica de vídeos — instruções para o Claude Code

Este repositório é a fábrica de vídeos do canal **JM Lab** (redes, homelab e tecnologia explicada, PT-BR).
O JM conversa com você em português; você opera a fábrica. **Nada é publicado sem o JM aprovar.**

## Estrutura
- `canal/config.json` — nome, cores, voz, ritmo de postagem.
- `canal/estilo.md` — tom e regras de roteiro do canal. Leia antes de escrever qualquer roteiro.
- `engine/` — motor de cenas (Remotion/React). Tipos do roteiro em `engine/src/types.ts`.
- `pipeline/fabrica.py` — linha de comando: `preparar`, `renderizar`, `mixar`, `tudo`.
- `videos/<slug>/roteiro.json` — um vídeo por pasta. `videos/<slug>/fontes.md` — fontes do roteiro.

## Fazer um vídeo novo ("faz um vídeo sobre X")
1. Leia `canal/estilo.md` e os títulos em `videos/*/roteiro.json` para não repetir tema nem ângulo.
2. Pesquise o tema na web. Anote cada fato com link em `videos/<slug>/fontes.md`.
   Não invente comandos, números ou datas: se não confirmou, não entra.
3. Escreva `videos/<slug>/roteiro.json` seguindo `engine/src/types.ts`:
   - cada bloco = 1 a 3 frases de narração + 1 cena;
   - varie as cenas (diagrama, terminal, lista, comparação, número, linha do tempo, frase);
   - abra com gancho em até 10 s (cena `abertura`), feche com `encerramento`;
   - comandos em cena `terminal` devem ser reais e testáveis (RouterOS, Linux, Proxmox…).
   - inclua o bloco `publicacao` (veja o vídeo demo): 3 `titulos` (até 100 caracteres), `resumo`,
     `tags`, `comentarioFixado` e `thumbnail` (`texto` de 2 a 5 palavras, `destaque`, `selo`, `icones`).
4. Mostre o roteiro ao JM e espere ele aprovar ou ajustar.
5. Rode `powershell -ExecutionPolicy Bypass -File .\produzir.ps1 videos\<slug>` (voz + longo + short + thumbnails + kit).
6. Peça ao JM para revisar na Central (`FABRICA.bat`) e clicar em Aprovar.

## Regras
- Português do Brasil, linguagem de conversa, sem jargão sem explicar.
- Nunca suba credenciais (`client_secret*.json`, `token*.json`) nem a amostra de voz.
- Não publique nada como público; uploads sempre `private` com data marcada, após aprovação.
