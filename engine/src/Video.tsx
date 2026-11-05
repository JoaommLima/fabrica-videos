import React from 'react';
import { AbsoluteFill, Series, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Bloco, Roteiro } from './types';
import { TemaCtx, Transicao, useLayout, useTema } from './components/base';
import * as C from './scenes/Cenas';

const CenaDoBloco: React.FC<{ bloco: Bloco; duracaoFrames: number }> = ({ bloco, duracaoFrames }) => {
  const c = bloco.cena;
  const p = { duracaoFrames } as const;
  switch (c.tipo) {
    case 'abertura': return <C.Abertura cena={c} {...p} />;
    case 'lista': return <C.Lista cena={c} {...p} />;
    case 'diagrama': return <C.Diagrama cena={c} {...p} />;
    case 'terminal': return <C.Terminal cena={c} {...p} />;
    case 'comparacao': return <C.Comparacao cena={c} {...p} />;
    case 'numero': return <C.Numero cena={c} {...p} />;
    case 'frase': return <C.Frase cena={c} {...p} />;
    case 'linha-do-tempo': return <C.LinhaDoTempo cena={c} {...p} />;
    case 'encerramento': return <C.Encerramento cena={c} {...p} />;
  }
};

const Fundo: React.FC = () => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { u } = useLayout();
  const passo = 60 * u;
  const desloc = (frame * 0.25 * u) % passo;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 30% 20%, ${tema.corFundo2} 0%, ${tema.corFundo} 70%)` }}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)`,
          backgroundSize: `${passo}px ${passo}px`,
          backgroundPosition: `${desloc}px ${desloc}px`,
        }}
      />
    </AbsoluteFill>
  );
};

const Marca: React.FC = () => {
  const tema = useTema();
  const { u, vertical } = useLayout();
  return (
    <div
      style={{
        position: 'absolute',
        left: (vertical ? 70 : 150) * u,
        top: (vertical ? 150 : 50) * u,
        fontFamily: tema.fonteCodigo,
        fontWeight: 700,
        fontSize: 24 * u,
        color: tema.corSuave,
        letterSpacing: 3 * u,
        display: 'flex',
        alignItems: 'center',
        gap: 12 * u,
      }}
    >
      <div style={{ width: 14 * u, height: 14 * u, borderRadius: 4 * u, background: tema.corDestaque }} />
      {tema.nomeCanal.toUpperCase()}
    </div>
  );
};

const Progresso: React.FC = () => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { u } = useLayout();
  return (
    <div style={{ position: 'absolute', left: 0, bottom: 0, height: 6 * u, width: `${(frame / durationInFrames) * 100}%`, background: tema.corDestaque, opacity: 0.8 }} />
  );
};

/** Legenda palavra por palavra (estilo Shorts), a partir dos tempos do Whisper. */
const Legenda: React.FC<{ roteiro: Roteiro }> = ({ roteiro }) => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { u, vertical } = useLayout();
  const t = frame / fps;
  const palavras = roteiro.legendas ?? [];
  const i = palavras.findIndex((p) => t >= p.inicio && t < p.fim + 0.15);
  if (i < 0) return null;
  const grupo = vertical ? 3 : 6;
  const ini = Math.floor(i / grupo) * grupo;
  const trecho = palavras.slice(ini, ini + grupo);
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: (vertical ? 300 : 70) * u, display: 'flex', justifyContent: 'center' }}>
      <div
        style={{
          background: 'rgba(0,0,0,0.6)',
          borderRadius: 14 * u,
          padding: `${10 * u}px ${24 * u}px`,
          fontFamily: tema.fonteTexto,
          fontWeight: 800,
          fontSize: (vertical ? 64 : 40) * u,
          maxWidth: '85%',
          textAlign: 'center',
        }}
      >
        {trecho.map((p, k) => (
          <span key={k} style={{ color: ini + k === i ? tema.corDestaque : tema.corTexto }}>
            {p.texto}{' '}
          </span>
        ))}
      </div>
    </div>
  );
};

export const Video: React.FC<Roteiro> = (roteiro) => {
  const { fps } = useVideoConfig();
  return (
    <TemaCtx.Provider value={roteiro.tema}>
      <AbsoluteFill style={{ fontFamily: roteiro.tema.fonteTexto }}>
        <Fundo />
        <Series>
          {roteiro.blocos.map((b) => {
            const d = Math.max(1, Math.round(b.duracao * fps));
            return (
              <Series.Sequence key={b.id} durationInFrames={d} name={`${b.id} · ${b.cena.tipo}`}>
                <Transicao duracaoFrames={d}>
                  <CenaDoBloco bloco={b} duracaoFrames={d} />
                </Transicao>
              </Series.Sequence>
            );
          })}
        </Series>
        <Marca />
        {roteiro.mostrarLegenda !== false && <Legenda roteiro={roteiro} />}
        <Progresso />
      </AbsoluteFill>
    </TemaCtx.Provider>
  );
};
