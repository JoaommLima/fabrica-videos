import React from 'react';
import { interpolate, useCurrentFrame, useVideoConfig, Easing } from 'remotion';
import type { Cena } from '../types';
import { Palco, Sublinhado, Surge, Titulo, useEntrada, useLayout, useTema } from '../components/base';
import { Icone } from '../components/Icones';

type P<T extends Cena['tipo']> = { cena: Extract<Cena, { tipo: T }>; duracaoFrames: number };

/** Distribui as entradas dos itens ao longo da primeira parte da narração. */
const passo = (n: number, duracaoFrames: number, inicio = 18) => Math.max(8, Math.min(40, (duracaoFrames * 0.6 - inicio) / Math.max(1, n)));

// ───────────────────────── ABERTURA ─────────────────────────
export const Abertura: React.FC<P<'abertura'>> = ({ cena }) => {
  const tema = useTema();
  const { u, vertical } = useLayout();
  return (
    <Palco centro>
      {cena.selo && (
        <Surge>
          <div
            style={{
              fontFamily: tema.fonteCodigo,
              fontSize: 26 * u,
              color: tema.corDestaque,
              border: `${2 * u}px solid ${tema.corDestaque}`,
              borderRadius: 999,
              padding: `${8 * u}px ${24 * u}px`,
              marginBottom: 36 * u,
              letterSpacing: 2 * u,
            }}
          >
            {cena.selo}
          </div>
        </Surge>
      )}
      <Titulo tamanho={vertical ? 96 : 110} atraso={4}>
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
  const s = passo(cena.itens.length, duracaoFrames);
  return (
    <Palco>
      <Titulo>{cena.titulo}</Titulo>
      <Sublinhado />
      <div style={{ marginTop: 60 * u, display: 'flex', flexDirection: 'column', gap: 30 * u }}>
        {cena.itens.map((item, i) => (
          <Surge key={i} atraso={18 + i * s} de="esquerda">
            <div style={{ display: 'flex', alignItems: 'center', gap: 28 * u }}>
              <div
                style={{
                  width: 64 * u,
                  height: 64 * u,
                  flexShrink: 0,
                  borderRadius: 16 * u,
                  background: tema.corDestaque,
                  color: tema.corFundo,
                  fontFamily: tema.fonteCodigo,
                  fontWeight: 700,
                  fontSize: 32 * u,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {i + 1}
              </div>
              <div style={{ fontFamily: tema.fonteTexto, fontWeight: 600, fontSize: 46 * u, color: tema.corTexto }}>{item}</div>
            </div>
          </Surge>
        ))}
      </div>
    </Palco>
  );
};

// ───────────────────────── DIAGRAMA DE REDE ─────────────────────────
export const Diagrama: React.FC<P<'diagrama'>> = ({ cena, duracaoFrames }) => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { u, vertical, width, height } = useLayout();
  const paleta = [tema.corDestaque, tema.corDestaque2, tema.corPerigo, '#c084fc'];
  const gruposIds = Object.keys(cena.grupos ?? {});
  const corDe = (g?: string) => (g ? paleta[gruposIds.indexOf(g) % paleta.length] : tema.corSuave);

  // Área do diagrama (px)
  const topo = cena.titulo ? (vertical ? 480 : 260) * u : 120 * u;
  const area = { x: (vertical ? 90 : 220) * u, y: topo, w: width - (vertical ? 180 : 440) * u, h: height - topo - (vertical ? 640 : 260) * u };
  const pos = (id: string) => {
    const n = cena.nos.find((n) => n.id === id)!;
    return { x: area.x + (n.x / 100) * area.w, y: area.y + (n.y / 100) * area.h };
  };
  const s = passo(cena.nos.length, duracaoFrames, 10) * 0.6;
  const fimNos = 10 + cena.nos.length * s;

  // Pacote viajando pelo caminho
  let pacote: { x: number; y: number } | null = null;
  if (cena.pacote && cena.pacote.length > 1) {
    const ini = fimNos + 15;
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

  return (
    <>
      {cena.titulo && (
        <Palco>
          <Titulo>{cena.titulo}</Titulo>
          <Sublinhado />
        </Palco>
      )}
      <svg style={{ position: 'absolute', inset: 0 }} width={width} height={height}>
        {cena.ligacoes.map(([a, b], i) => {
          const pa = pos(a);
          const pb = pos(b);
          const prog = interpolate(frame, [fimNos * 0.5 + i * 3, fimNos * 0.5 + i * 3 + 18], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
          return (
            <line
              key={i}
              x1={pa.x}
              y1={pa.y}
              x2={pa.x + (pb.x - pa.x) * prog}
              y2={pa.y + (pb.y - pa.y) * prog}
              stroke={tema.corSuave}
              strokeOpacity={0.55}
              strokeWidth={4 * u}
              strokeDasharray={`${10 * u} ${8 * u}`}
              strokeDashoffset={-frame * 1.2 * u}
            />
          );
        })}
        {pacote && (
          <>
            <circle cx={pacote.x} cy={pacote.y} r={26 * u} fill={tema.corDestaque} opacity={0.25} />
            <circle cx={pacote.x} cy={pacote.y} r={13 * u} fill={tema.corDestaque} />
          </>
        )}
      </svg>
      {cena.nos.map((n, i) => {
        const p = pos(n.id);
        const e = useEntrada(10 + i * s);
        const cor = corDe(n.grupo);
        return (
          <div
            key={n.id}
            style={{
              position: 'absolute',
              left: p.x,
              top: p.y,
              transform: `translate(-50%, -50%) scale(${0.6 + 0.4 * e})`,
              opacity: e,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <div
              style={{
                width: tamIcone * 1.55,
                height: tamIcone * 1.55,
                borderRadius: 28 * u,
                background: tema.corFundo2,
                border: `${3 * u}px solid ${cor}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: `0 ${10 * u}px ${30 * u}px rgba(0,0,0,0.35)`,
              }}
            >
              <Icone nome={n.icone} cor={cor} tamanho={tamIcone} />
            </div>
            <div style={{ marginTop: 14 * u, fontFamily: tema.fonteTexto, fontWeight: 600, fontSize: 30 * u, color: tema.corTexto, whiteSpace: 'nowrap' }}>{n.rotulo}</div>
          </div>
        );
      })}
      {gruposIds.length > 0 && (
        <div style={{ position: 'absolute', left: (vertical ? 70 : 150) * u, bottom: (vertical ? 470 : 70) * u, display: 'flex', flexDirection: vertical ? 'column' : 'row', gap: (vertical ? 12 : 36) * u }}>
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
  const vel = Math.max(1.2, totalChars / Math.max(30, duracaoFrames * 0.7 - 20)); // caracteres por frame
  let orcamento = Math.max(0, (frame - 20) * vel);
  return (
    <Palco>
      {cena.titulo && (
        <>
          <Titulo>{cena.titulo}</Titulo>
          <Sublinhado />
        </>
      )}
      <Surge atraso={6} de="zoom" style={{ marginTop: (cena.titulo ? 50 : 0) * u, flex: 1 }}>
        <div style={{ background: '#0b0f14', borderRadius: 20 * u, border: `${2 * u}px solid #263040`, height: '100%', overflow: 'hidden', boxShadow: `0 ${20 * u}px ${60 * u}px rgba(0,0,0,0.5)` }}>
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
                      <span style={{ color: tema.corDestaque }}>{prompt} </span>
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
  const s = passo(n * 2, duracaoFrames, 24);
  const Coluna: React.FC<{ lado: 'esquerda' | 'direita'; cor: string }> = ({ lado, cor }) => {
    const c = cena[lado];
    return (
      <Surge atraso={lado === 'esquerda' ? 10 : 18} de={lado === 'esquerda' ? 'esquerda' : 'direita'} style={{ flex: 1, minWidth: 0 }}>
        <div style={{ background: tema.corFundo2, borderRadius: 28 * u, padding: 44 * u, borderTop: `${8 * u}px solid ${cor}` }}>
          <div style={{ fontFamily: tema.fonteTexto, fontWeight: 800, fontSize: 48 * u, color: cor, marginBottom: 30 * u }}>{c.titulo}</div>
          {c.itens.map((it, i) => (
            <Surge key={i} atraso={24 + (i * 2 + (lado === 'direita' ? 1 : 0)) * s}>
              <div style={{ fontFamily: tema.fonteTexto, fontSize: 36 * u, color: tema.corTexto, padding: `${14 * u}px 0`, borderBottom: `${1 * u}px solid rgba(255,255,255,0.08)` }}>
                {it}
              </div>
            </Surge>
          ))}
        </div>
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
      <div style={{ display: 'flex', flexDirection: vertical ? 'column' : 'row', alignItems: 'flex-start', gap: 40 * u, marginTop: 60 * u }}>
        <Coluna lado="esquerda" cor={tema.corDestaque2} />
        <Coluna lado="direita" cor={tema.corDestaque} />
      </div>
    </Palco>
  );
};

// ───────────────────────── NÚMERO ─────────────────────────
export const Numero: React.FC<P<'numero'>> = ({ cena, duracaoFrames }) => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { u, vertical } = useLayout();
  const t = interpolate(frame, [8, Math.min(70, duracaoFrames * 0.5)], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
  const v = (cena.valor * t).toLocaleString('pt-BR', { minimumFractionDigits: cena.casas ?? 0, maximumFractionDigits: cena.casas ?? 0 });
  return (
    <Palco centro>
      <Surge de="zoom">
        <div style={{ fontFamily: tema.fonteTexto, fontWeight: 800, fontSize: (vertical ? 190 : 230) * u, color: tema.corDestaque, letterSpacing: -6 * u, lineHeight: 1 }}>
          {cena.prefixo}
          {v}
          {cena.sufixo}
        </div>
      </Surge>
      <Surge atraso={16}>
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
        <div style={{ fontFamily: tema.fonteTexto, fontWeight: 800, fontSize: 160 * u, color: tema.corDestaque, lineHeight: 0.6, height: 80 * u }}>“</div>
      </Surge>
      <Surge atraso={6}>
        <div style={{ fontFamily: tema.fonteTexto, fontWeight: 600, fontSize: (vertical ? 62 : 68) * u, color: tema.corTexto, maxWidth: 1400 * u, lineHeight: 1.25 }}>{cena.texto}</div>
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
  const s = passo(cena.marcos.length, duracaoFrames, 20);
  const prog = interpolate(frame, [14, 20 + cena.marcos.length * s], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
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
            background: tema.corDestaque,
            ...(vertical ? { left: 22 * u, top: 0, width: 6 * u, height: `${prog * 100}%` } : { left: 0, top: '50%', height: 6 * u, width: `${prog * 100}%` }),
          }}
        />
        {cena.marcos.map((m, i) => (
          <Surge key={i} atraso={20 + i * s} style={{ flex: 1, position: 'relative' }}>
            <div style={{ display: 'flex', flexDirection: vertical ? 'row' : 'column', alignItems: vertical ? 'center' : 'flex-start', gap: 20 * u, paddingLeft: vertical ? 0 : 10 * u }}>
              <div style={{ width: 50 * u, height: 50 * u, borderRadius: 99, background: tema.corFundo, border: `${6 * u}px solid ${tema.corDestaque}`, flexShrink: 0 }} />
              <div>
                <div style={{ fontFamily: tema.fonteCodigo, fontWeight: 700, fontSize: 40 * u, color: tema.corDestaque }}>{m.ano}</div>
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
  const pulso = 1 + 0.04 * Math.sin((frame / fps) * Math.PI * 2);
  return (
    <Palco centro>
      <Titulo tamanho={90}>{cena.titulo}</Titulo>
      {cena.texto && (
        <Surge atraso={10}>
          <div style={{ fontFamily: tema.fonteTexto, fontSize: 40 * u, color: tema.corSuave, marginTop: 26 * u, maxWidth: 1300 * u }}>{cena.texto}</div>
        </Surge>
      )}
      <Surge atraso={22} de="zoom">
        <div
          style={{
            marginTop: 60 * u,
            transform: `scale(${pulso})`,
            background: tema.corDestaque,
            color: tema.corFundo,
            fontFamily: tema.fonteTexto,
            fontWeight: 800,
            fontSize: 44 * u,
            padding: `${22 * u}px ${56 * u}px`,
            borderRadius: 999,
          }}
        >
          Inscreva-se
        </div>
      </Surge>
    </Palco>
  );
};
