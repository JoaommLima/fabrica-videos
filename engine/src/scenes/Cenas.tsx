import React, { useContext } from 'react';
import { interpolate, useCurrentFrame, useVideoConfig, Easing } from 'remotion';
import type { Cena } from '../types';
import { BlocoCtx, Cartao, Palco, Sublinhado, Surge, Titulo, useEntrada, useGatilhos, useLayout, useTema } from '../components/base';
import { Icone } from '../components/Icones';
import { Som } from '../components/Som';

type P<T extends Cena['tipo']> = { cena: Extract<Cena, { tipo: T }>; duracaoFrames: number };

const passo = (n: number, duracaoFrames: number, inicio = 18) => Math.max(8, Math.min(40, (duracaoFrames * 0.6 - inicio) / Math.max(1, n)));

/** Frame (no bloco) em que a narração fala um número/termo — para o contador começar junto. */
const useMomento = (alvo: string, padrao: number) => useGatilhos([alvo], undefined, padrao, 0)[0];

// ───────────────────────── ABERTURA ─────────────────────────
export const Abertura: React.FC<P<'abertura'>> = ({ cena }) => {
  const tema = useTema();
  const { u, vertical } = useLayout();
  return (
    <Palco centro={tema.estilo !== 'revista'} style={tema.estilo === 'revista' ? { justifyContent: 'center' } : undefined}>
      {cena.selo && (
        <Surge>
          <div
            style={{
              display: 'inline-block',
              fontFamily: tema.fonteCodigo,
              fontSize: 26 * u,
              color: tema.estilo === 'revista' ? tema.corSobreDestaque : tema.corDestaque === '#ffd93b' ? tema.corTexto : tema.corDestaque,
              background: tema.estilo === 'revista' ? tema.corDestaque : tema.estilo === 'caderno' ? tema.corDestaque : 'transparent',
              border: tema.estilo === 'neon' || tema.estilo === 'bancada' ? `${2 * u}px solid ${tema.corDestaque}` : 'none',
              borderRadius: tema.estilo === 'neon' ? 999 : tema.raio * u,
              padding: `${8 * u}px ${24 * u}px`,
              marginBottom: 36 * u,
              letterSpacing: 2 * u,
              transform: tema.estilo === 'caderno' ? 'rotate(-2deg)' : undefined,
            }}
          >
            {cena.selo}
          </div>
        </Surge>
      )}
      <Som tipo="whoosh" em={2} volume={0.7} />
      {cena.selo && <Som tipo="clique" em={0} volume={0.6} />}
      <Titulo tamanho={vertical ? 96 : 110} atraso={4} centro={tema.estilo !== 'revista'}>
        {cena.titulo}
      </Titulo>
      {cena.subtitulo && (
        <Surge atraso={14}>
          <div style={{ fontFamily: tema.fonteTexto, fontSize: 40 * u, color: tema.corSuave, marginTop: 30 * u, maxWidth: 1300 * u }}>{cena.subtitulo}</div>
        </Surge>
      )}
    </Palco>
  );
};

// ───────────────────────── LISTA ─────────────────────────
export const Lista: React.FC<P<'lista'>> = ({ cena, duracaoFrames }) => {
  const tema = useTema();
  const { u } = useLayout();
  const quando = useGatilhos(cena.itens, cena.gatilhos, 18, passo(cena.itens.length, duracaoFrames));
  return (
    <Palco>
      <Titulo>{cena.titulo}</Titulo>
      <Sublinhado />
      <div style={{ marginTop: 60 * u, display: 'flex', flexDirection: 'column', gap: 30 * u }}>
        {cena.itens.map((item, i) => (
          <Surge key={i} atraso={quando[i]} de="esquerda">
            <Som tipo="pop" em={quando[i]} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 28 * u }}>
              <Marcador n={i + 1} />
              <div style={{ fontFamily: tema.fonteTexto, fontWeight: 600, fontSize: 46 * u, color: tema.corTexto }}>{item}</div>
            </div>
          </Surge>
        ))}
      </div>
    </Palco>
  );
};

const Marcador: React.FC<{ n: number }> = ({ n }) => {
  const tema = useTema();
  const { u } = useLayout();
  const s = 64 * u;
  if (tema.estilo === 'caderno') {
    return (
      <div style={{ width: s, height: s, flexShrink: 0, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <svg width={s} height={s} viewBox="0 0 64 64" style={{ position: 'absolute', inset: 0 }}>
          <circle cx="32" cy="32" r="26" fill="none" stroke={tema.corDestaque2} strokeWidth={4} filter="url(#rabisco)" />
        </svg>
        <span style={{ fontFamily: tema.fonteTitulo, fontWeight: 700, fontSize: 44 * u, color: tema.corDestaque2 }}>{n}</span>
      </div>
    );
  }
  if (tema.estilo === 'revista') {
    return <div style={{ width: s, flexShrink: 0, fontFamily: tema.fonteTitulo, fontWeight: 800, fontSize: 56 * u, color: tema.corDestaque }}>{String(n).padStart(2, '0')}</div>;
  }
  return (
    <div
      style={{
        width: s,
        height: s,
        flexShrink: 0,
        borderRadius: (tema.estilo === 'bancada' ? 4 : 16) * u,
        background: tema.corDestaque,
        color: tema.corSobreDestaque,
        fontFamily: tema.fonteCodigo,
        fontWeight: 700,
        fontSize: 32 * u,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {n}
    </div>
  );
};

// ───────────────────────── DIAGRAMA DE REDE ─────────────────────────
export const Diagrama: React.FC<P<'diagrama'>> = ({ cena, duracaoFrames }) => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { u, vertical, width, height } = useLayout();
  const paleta = [...new Set([tema.corDestaque2, tema.estilo === 'caderno' ? '#2e9e6b' : tema.corDestaque, tema.corPerigo, '#2e9e6b', '#9b6bd6'])];
  const gruposIds = Object.keys(cena.grupos ?? {});
  const corDe = (g?: string) => (g ? paleta[gruposIds.indexOf(g) % paleta.length] : tema.estilo === 'neon' ? tema.corSuave : tema.corLinha);

  const topo = cena.titulo ? (vertical ? 480 : 310) * u : 120 * u;
  const area = { x: (vertical ? 90 : 220) * u, y: topo, w: width - (vertical ? 180 : 440) * u, h: height - topo - (vertical ? 640 : 260) * u };
  const pos = (id: string) => {
    const n = cena.nos.find((n) => n.id === id)!;
    return { x: area.x + (n.x / 100) * area.w, y: area.y + (n.y / 100) * area.h };
  };
  // cada aparelho aparece quando é citado na narração
  const quando = useGatilhos(cena.nos.map((n) => n.rotulo), cena.gatilhos, 10, passo(cena.nos.length, duracaoFrames, 10) * 0.6);
  const quandoDe = (id: string) => quando[cena.nos.findIndex((n) => n.id === id)];
  const fimNos = Math.max(...quando);

  let pacote: { x: number; y: number } | null = null;
  if (cena.pacote && cena.pacote.length > 1) {
    const ini = fimNos + 12;
    const dur = Math.max(30, duracaoFrames - ini - 25);
    const t = interpolate(frame, [ini, ini + dur], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic) });
    if (frame >= ini) {
      const segs = cena.pacote.length - 1;
      const k = Math.min(segs - 1, Math.floor(t * segs));
      const lt = t * segs - k;
      const a = pos(cena.pacote[k]);
      const b = pos(cena.pacote[k + 1]);
      pacote = { x: a.x + (b.x - a.x) * lt, y: a.y + (b.y - a.y) * lt };
    }
  }
  const tamIcone = (vertical ? 100 : 92) * u;
  const corLigacao = tema.estilo === 'neon' ? tema.corSuave : tema.corLinha;

  return (
    <>
      {cena.titulo && (
        <Palco>
          <Titulo>{cena.titulo}</Titulo>
          <Sublinhado />
        </Palco>
      )}
      <svg style={{ position: 'absolute', inset: 0, overflow: 'visible' }} width={width} height={height}>
        {cena.ligacoes.map(([a, b], i) => {
          const pa = pos(a);
          const pb = pos(b);
          const ini = Math.max(quandoDe(a), quandoDe(b));
          const prog = interpolate(frame, [ini, ini + 14], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
          return (
            <line
              key={i}
              x1={pa.x}
              y1={pa.y}
              x2={pa.x + (pb.x - pa.x) * prog}
              y2={pa.y + (pb.y - pa.y) * prog}
              stroke={corLigacao}
              strokeOpacity={tema.estilo === 'neon' ? 0.55 : 0.8}
              strokeWidth={(tema.estilo === 'revista' ? 3 : 4) * u}
              strokeLinecap="round"
              strokeDasharray={tema.estilo === 'revista' || tema.estilo === 'caderno' ? undefined : `${10 * u} ${8 * u}`}
              strokeDashoffset={-frame * 1.2 * u}
              filter={tema.rabisco ? 'url(#rabisco)' : undefined}
            />
          );
        })}
        {pacote && (
          <>
            <circle cx={pacote.x} cy={pacote.y} r={26 * u} fill={tema.corPerigo} opacity={0.25} />
            <circle cx={pacote.x} cy={pacote.y} r={13 * u} fill={tema.corPerigo} />
          </>
        )}
      </svg>
      {cena.nos.map((_, i) => (
        <Som key={`s${i}`} tipo="pop" em={quando[i]} volume={0.85} />
      ))}
      {cena.pacote && cena.pacote.length > 1 && <Som tipo="whoosh" em={fimNos + 12} volume={0.5} />}
      {cena.nos.map((n, i) => {
        const p = pos(n.id);
        const e = useEntrada(quando[i]);
        const cor = corDe(n.grupo);
        return (
          <div
            key={n.id}
            style={{
              position: 'absolute',
              left: p.x,
              top: p.y,
              transform: `translate(-50%, -50%) scale(${0.6 + 0.4 * e}) rotate(${tema.estilo === 'caderno' ? (i % 2 ? 1.5 : -1.5) : 0}deg)`,
              opacity: e,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <Cartao cor={cor} style={{ width: tamIcone * 1.55, height: tamIcone * 1.55, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ width: tamIcone * 1.55, height: tamIcone * 1.55, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icone nome={n.icone} cor={cor} tamanho={tamIcone} />
              </div>
            </Cartao>
            <div
              style={{
                marginTop: 14 * u,
                fontFamily: tema.estilo === 'caderno' ? tema.fonteTitulo : tema.fonteTexto,
                fontWeight: tema.estilo === 'caderno' ? 700 : 600,
                fontSize: (tema.estilo === 'caderno' ? 40 : 30) * u,
                color: tema.corTexto,
                whiteSpace: 'nowrap',
              }}
            >
              {n.rotulo}
            </div>
          </div>
        );
      })}
      {gruposIds.length > 0 && (
        <div style={{ position: 'absolute', ...(vertical ? { left: 70 * u, bottom: 470 * u, flexDirection: 'column' } : { right: 150 * u, top: 150 * u, flexDirection: 'row' }), display: 'flex', gap: (vertical ? 14 : 32) * u }}>
          {gruposIds.map((g) => (
            <Surge key={g} atraso={fimNos}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 * u, fontFamily: tema.fonteCodigo, fontSize: 26 * u, color: tema.corTexto }}>
                <div style={{ width: 22 * u, height: 22 * u, borderRadius: 6 * u, background: corDe(g) }} />
                {cena.grupos![g]}
              </div>
            </Surge>
          ))}
        </div>
      )}
    </>
  );
};

// ───────────────────────── TERMINAL ─────────────────────────
export const Terminal: React.FC<P<'terminal'>> = ({ cena, duracaoFrames }) => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { u } = useLayout();
  const prompt = cena.prompt ?? '[admin@MikroTik] >';
  const totalChars = cena.linhas.reduce((s, l) => s + (l.cmd?.length ?? 0) + 12, 0);
  const vel = Math.max(1.2, totalChars / Math.max(30, duracaoFrames * 0.7 - 20));
  let orcamento = Math.max(0, (frame - 20) * vel);
  // sons de teclado: um clique a cada 2 caracteres, alternando 3 timbres; "enter" no fim de cada comando
  const sons: React.ReactNode[] = [];
  let acumulado = 0;
  cena.linhas.forEach((l, li) => {
    const n = l.cmd?.length ?? 0;
    for (let j = 0; j < n; j += 2) {
      sons.push(<Som key={`k${li}-${j}`} tipo={(['tecla1', 'tecla2', 'tecla3'] as const)[(j / 2 + li) % 3]} em={20 + (acumulado + j) / vel} volume={0.55} />);
    }
    if (n) sons.push(<Som key={`e${li}`} tipo="clique" em={20 + (acumulado + n) / vel + 2} volume={0.5} />);
    acumulado += n + 12;
  });
  return (
    <Palco>
      {sons}
      {cena.titulo && (
        <>
          <Titulo>{cena.titulo}</Titulo>
          <Sublinhado />
        </>
      )}
      <Surge atraso={6} de="zoom" style={{ marginTop: (cena.titulo ? 50 : 0) * u, flex: 1 }}>
        <div
          style={{
            background: '#0b0f14',
            borderRadius: Math.max(6, tema.raio) * u,
            border: `${2 * u}px solid #263040`,
            height: '100%',
            overflow: 'hidden',
            boxShadow: tema.estilo === 'revista' ? `${10 * u}px ${10 * u}px 0 ${tema.corLinha}` : `0 ${20 * u}px ${60 * u}px rgba(0,0,0,0.45)`,
            transform: tema.estilo === 'caderno' ? 'rotate(-0.6deg)' : undefined,
          }}
        >
          <div style={{ display: 'flex', gap: 12 * u, padding: `${18 * u}px ${24 * u}px`, borderBottom: `${2 * u}px solid #1c2430` }}>
            {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
              <div key={c} style={{ width: 18 * u, height: 18 * u, borderRadius: 99, background: c }} />
            ))}
          </div>
          <div style={{ padding: 36 * u, fontFamily: tema.fonteCodigo, fontSize: 32 * u, lineHeight: 1.55 }}>
            {cena.linhas.map((l, i) => {
              if (orcamento <= 0) return null;
              const cmd = l.cmd ?? '';
              const mostrados = Math.min(cmd.length, Math.floor(orcamento));
              orcamento -= cmd.length + 12;
              const digitando = mostrados < cmd.length;
              return (
                <div key={i}>
                  {l.cmd !== undefined && (
                    <div>
                      <span style={{ color: tema.estilo === 'neon' ? tema.corDestaque : '#7ee2b8' }}>{prompt} </span>
                      <span style={{ color: '#e6edf3' }}>{cmd.slice(0, mostrados)}</span>
                      {digitando && <span style={{ background: '#e6edf3', opacity: Math.floor(frame / 8) % 2 ? 1 : 0.2 }}>&nbsp;</span>}
                    </div>
                  )}
                  {!digitando && l.saida && <div style={{ color: '#8b98a9', whiteSpace: 'pre' }}>{l.saida}</div>}
                </div>
              );
            })}
          </div>
        </div>
      </Surge>
    </Palco>
  );
};

// ───────────────────────── COMPARAÇÃO ─────────────────────────
export const Comparacao: React.FC<P<'comparacao'>> = ({ cena, duracaoFrames }) => {
  const tema = useTema();
  const { u, vertical } = useLayout();
  const n = Math.max(cena.esquerda.itens.length, cena.direita.itens.length);
  // as colunas aparecem quando os títulos são falados; os itens de cada lado vêm em seguida
  const [qe, qd] = useGatilhos([cena.esquerda.titulo, cena.direita.titulo], undefined, 10, passo(2, duracaoFrames, 10));
  const s = passo(n * 2, duracaoFrames, 24) * 0.7;
  const corE = tema.corDestaque2;
  const corD = tema.estilo === 'caderno' ? tema.corPerigo : tema.corDestaque;
  const Coluna: React.FC<{ lado: 'esquerda' | 'direita'; cor: string; ini: number }> = ({ lado, cor, ini }) => {
    const c = cena[lado];
    return (
      <Surge atraso={ini} de={lado === 'esquerda' ? 'esquerda' : 'direita'} style={{ flex: 1, minWidth: 0 }}>
        <Som tipo="whoosh" em={ini} volume={0.55} />
        <Cartao topo={tema.estilo === 'caderno' ? undefined : cor} style={{ padding: 44 * u }}>
          <div style={{ fontFamily: tema.fonteTitulo, fontWeight: tema.pesoTitulo, fontSize: (tema.estilo === 'caderno' ? 62 : 48) * u, color: cor, marginBottom: 30 * u }}>{c.titulo}</div>
          {c.itens.map((it, i) => (
            <Surge key={i} atraso={ini + 10 + i * s}>
              <div style={{ fontFamily: tema.fonteTexto, fontSize: 36 * u, color: tema.corTexto, padding: `${14 * u}px 0`, borderBottom: `${1 * u}px solid ${tema.corLinha}22` }}>{it}</div>
            </Surge>
          ))}
        </Cartao>
      </Surge>
    );
  };
  return (
    <Palco>
      {cena.titulo && (
        <>
          <Titulo>{cena.titulo}</Titulo>
          <Sublinhado />
        </>
      )}
      <div style={{ display: 'flex', flexDirection: vertical ? 'column' : 'row', alignItems: 'flex-start', gap: 48 * u, marginTop: 60 * u }}>
        <Coluna lado="esquerda" cor={corE} ini={qe} />
        <Coluna lado="direita" cor={corD} ini={qd} />
      </div>
    </Palco>
  );
};

// ───────────────────────── NÚMERO ─────────────────────────
export const Numero: React.FC<P<'numero'>> = ({ cena, duracaoFrames }) => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { u, vertical } = useLayout();
  const { palavras } = useContext(BlocoCtx);
  // contador dispara quando a narração chega no número (procura palavras como "mil", "quatro")
  const ini = useMomento(String(cena.valor).length > 3 ? 'mil' : String(cena.valor), palavras.length ? 8 : 2);
  const t = interpolate(frame, [ini, ini + Math.min(45, duracaoFrames * 0.4)], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
  const durConta = Math.min(45, duracaoFrames * 0.4);
  const ticks = Array.from({ length: Math.floor(durConta / 4) }, (_, k) => <Som key={k} tipo="tick" em={ini + k * 4} volume={0.35 + 0.4 * (k / (durConta / 4))} />);
  const v = (cena.valor * t).toLocaleString('pt-BR', { minimumFractionDigits: cena.casas ?? 0, maximumFractionDigits: cena.casas ?? 0 });
  const cor = tema.estilo === 'caderno' ? tema.corDestaque2 : tema.corDestaque;
  return (
    <Palco centro>
      {ticks}
      <Som tipo="ding" em={ini + durConta} volume={0.7} />
      <Surge de="zoom">
        <div
          style={{
            fontFamily: tema.fonteTitulo,
            fontWeight: tema.pesoTitulo,
            fontSize: (vertical ? 190 : 230) * (tema.estilo === 'caderno' ? 1.25 : 1) * u,
            color: cor,
            letterSpacing: (tema.estilo === 'caderno' ? 0 : -6) * u,
            lineHeight: 1,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {cena.prefixo}
          {v}
          {cena.sufixo}
        </div>
      </Surge>
      <Surge atraso={ini + 10}>
        <div style={{ fontFamily: tema.fonteTexto, fontSize: 46 * u, color: tema.corTexto, marginTop: 30 * u, maxWidth: 1200 * u }}>{cena.legenda}</div>
      </Surge>
    </Palco>
  );
};

// ───────────────────────── FRASE ─────────────────────────
export const Frase: React.FC<P<'frase'>> = ({ cena }) => {
  const tema = useTema();
  const { u, vertical } = useLayout();
  return (
    <Palco centro>
      <Surge>
        <div style={{ fontFamily: tema.fonteTitulo, fontWeight: 800, fontSize: 160 * u, color: tema.estilo === 'caderno' ? tema.corPerigo : tema.corDestaque, lineHeight: 0.6, height: 80 * u }}>“</div>
      </Surge>
      <Surge atraso={6}>
        <div style={{ fontFamily: tema.fonteTitulo, fontWeight: tema.pesoTitulo, fontSize: (vertical ? 62 : 68) * (tema.estilo === 'caderno' ? 1.3 : 1) * u, color: tema.corTexto, maxWidth: 1400 * u, lineHeight: 1.2 }}>
          {cena.texto}
        </div>
      </Surge>
      {cena.autor && (
        <Surge atraso={18}>
          <div style={{ fontFamily: tema.fonteCodigo, fontSize: 30 * u, color: tema.corSuave, marginTop: 36 * u }}>— {cena.autor}</div>
        </Surge>
      )}
    </Palco>
  );
};

// ───────────────────────── LINHA DO TEMPO ─────────────────────────
export const LinhaDoTempo: React.FC<P<'linha-do-tempo'>> = ({ cena, duracaoFrames }) => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { u, vertical } = useLayout();
  const quando = useGatilhos(
    cena.marcos.map((m) => `${m.ano} ${m.texto}`),
    cena.gatilhos,
    20,
    passo(cena.marcos.length, duracaoFrames, 20),
  );
  const prog = interpolate(frame, [quando[0] - 6, quando[quando.length - 1] + 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <Palco>
      {cena.titulo && (
        <>
          <Titulo>{cena.titulo}</Titulo>
          <Sublinhado />
        </>
      )}
      <div style={{ position: 'relative', flex: 1, display: 'flex', flexDirection: vertical ? 'column' : 'row', justifyContent: 'space-between', alignItems: vertical ? 'stretch' : 'center', marginTop: 40 * u }}>
        <div
          style={{
            position: 'absolute',
            background: tema.estilo === 'neon' ? tema.corDestaque : tema.corLinha,
            filter: tema.rabisco ? 'url(#rabisco)' : undefined,
            ...(vertical ? { left: 22 * u, top: 0, width: 6 * u, height: `${prog * 100}%` } : { left: 0, top: '50%', height: 6 * u, width: `${prog * 100}%` }),
          }}
        />
        {cena.marcos.map((m, i) => (
          <Surge key={i} atraso={quando[i]} style={{ flex: 1, position: 'relative' }}>
            <Som tipo="pop" em={quando[i]} />
            <div style={{ display: 'flex', flexDirection: vertical ? 'row' : 'column', alignItems: vertical ? 'center' : 'flex-start', gap: 20 * u, paddingLeft: vertical ? 0 : 10 * u }}>
              <div style={{ width: 50 * u, height: 50 * u, borderRadius: 99, background: tema.corFundo, border: `${6 * u}px solid ${tema.estilo === 'caderno' ? tema.corPerigo : tema.corDestaque}`, flexShrink: 0 }} />
              <div>
                <div style={{ fontFamily: tema.fonteCodigo, fontWeight: 700, fontSize: 40 * u, color: tema.estilo === 'caderno' ? tema.corDestaque2 : tema.corDestaque }}>{m.ano}</div>
                <div style={{ fontFamily: tema.fonteTexto, fontSize: 32 * u, color: tema.corTexto, maxWidth: 360 * u, marginTop: 6 * u }}>{m.texto}</div>
              </div>
            </div>
          </Surge>
        ))}
      </div>
    </Palco>
  );
};

// ───────────────────────── ENCERRAMENTO ─────────────────────────
export const Encerramento: React.FC<P<'encerramento'>> = ({ cena }) => {
  const tema = useTema();
  const { u } = useLayout();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const quando = useGatilhos(['inscreve inscreva'], undefined, 22, 0)[0];
  const pulso = 1 + 0.04 * Math.sin((frame / fps) * Math.PI * 2);
  return (
    <Palco centro>
      <Titulo tamanho={90} centro>
        {cena.titulo}
      </Titulo>
      {cena.texto && (
        <Surge atraso={10}>
          <div style={{ fontFamily: tema.fonteTexto, fontSize: 40 * u, color: tema.corSuave, marginTop: 26 * u, maxWidth: 1300 * u }}>{cena.texto}</div>
        </Surge>
      )}
      <Som tipo="pop" em={quando} />
      <Som tipo="ding" em={quando + 4} volume={0.5} />
      <Surge atraso={quando} de="zoom">
        <div
          style={{
            marginTop: 60 * u,
            transform: `scale(${pulso}) rotate(${tema.estilo === 'caderno' ? -2 : 0}deg)`,
            background: tema.estilo === 'caderno' ? tema.corPerigo : tema.corDestaque,
            color: tema.estilo === 'caderno' ? '#fff' : tema.corSobreDestaque,
            fontFamily: tema.estilo === 'caderno' ? tema.fonteTitulo : tema.fonteTexto,
            fontWeight: 800,
            fontSize: (tema.estilo === 'caderno' ? 56 : 44) * u,
            padding: `${22 * u}px ${56 * u}px`,
            borderRadius: tema.estilo === 'neon' ? 999 : tema.raio * u,
            boxShadow: tema.estilo === 'revista' ? `${6 * u}px ${6 * u}px 0 ${tema.corLinha}` : undefined,
          }}
        >
          Inscreva-se
        </div>
      </Surge>
    </Palco>
  );
};
