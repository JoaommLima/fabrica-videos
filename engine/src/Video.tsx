import React from 'react';
import { AbsoluteFill, Series, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Bloco, Roteiro } from './types';
import { BlocoCtx, Filtros, Fundo, Grao, TemaCtx, Transicao, useLayout, useTema } from './components/base';
import * as C from './scenes/Cenas';
import { Som, VolumeSomCtx } from './components/Som';

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

const Marca: React.FC = () => {
  const tema = useTema();
  const { u, vertical } = useLayout();
  if (tema.estilo === 'bancada') return null; // o nome já aparece acima dos títulos
  const esq = (vertical ? 70 : 150) * u;
  if (tema.estilo === 'revista') {
    return (
      <div style={{ position: 'absolute', left: esq, right: esq, top: (vertical ? 150 : 46) * u, display: 'flex', justifyContent: 'space-between', borderBottom: `${2 * u}px solid ${tema.corLinha}`, paddingBottom: 8 * u, fontFamily: tema.fonteCodigo, fontSize: 22 * u, color: tema.corTexto, letterSpacing: 3 * u }}>
        <span style={{ fontWeight: 700 }}>{tema.nomeCanal.toUpperCase()}</span>
        <span style={{ color: tema.corSuave }}>REDES · HOMELAB · TECNOLOGIA</span>
      </div>
    );
  }
  return (
    <div
      style={{
        position: 'absolute',
        left: esq,
        top: (vertical ? 150 : 50) * u,
        fontFamily: tema.estilo === 'caderno' ? tema.fonteTitulo : tema.fonteCodigo,
        fontWeight: 700,
        fontSize: (tema.estilo === 'caderno' ? 36 : 24) * u,
        color: tema.corSuave,
        letterSpacing: (tema.estilo === 'caderno' ? 0 : 3) * u,
        display: 'flex',
        alignItems: 'center',
        gap: 12 * u,
      }}
    >
      {tema.estilo === 'neon' && <div style={{ width: 14 * u, height: 14 * u, borderRadius: 4 * u, background: tema.corDestaque }} />}
      {tema.estilo === 'caderno' ? tema.nomeCanal : tema.nomeCanal.toUpperCase()}
    </div>
  );
};

const Progresso: React.FC = () => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { u } = useLayout();
  const cor = tema.estilo === 'caderno' ? tema.corPerigo : tema.corDestaque;
  return <div style={{ position: 'absolute', left: 0, bottom: 0, height: 6 * u, width: `${(frame / durationInFrames) * 100}%`, background: cor, opacity: 0.85 }} />;
};

/** Legenda palavra por palavra, a partir dos tempos reais da fala. */
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
  const claro = tema.estilo === 'caderno' || tema.estilo === 'revista';
  const caixa: React.CSSProperties =
    tema.estilo === 'revista'
      ? { background: tema.corLinha, borderRadius: 0 }
      : tema.estilo === 'caderno'
        ? { background: 'transparent' }
        : { background: 'rgba(0,0,0,0.6)', borderRadius: 14 * u };
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: (vertical ? 300 : 70) * u, display: 'flex', justifyContent: 'center' }}>
      <div style={{ ...caixa, padding: `${10 * u}px ${24 * u}px`, fontFamily: tema.fonteTexto, fontWeight: 800, fontSize: (vertical ? 64 : 40) * u, maxWidth: '85%', textAlign: 'center' }}>
        {trecho.map((p, k) => {
          const atual = ini + k === i;
          if (tema.estilo === 'caderno') {
            return (
              <span key={k} style={{ color: tema.corTexto, background: atual ? tema.corDestaque : 'transparent', borderRadius: 4 * u, padding: `0 ${4 * u}px` }}>
                {p.texto}{' '}
              </span>
            );
          }
          const corBase = tema.estilo === 'revista' ? '#ffffff' : claro ? tema.corTexto : tema.corTexto;
          return (
            <span key={k} style={{ color: atual ? tema.corDestaque : corBase }}>
              {p.texto}{' '}
            </span>
          );
        })}
      </div>
    </div>
  );
};

export const Video: React.FC<Roteiro> = (roteiro) => {
  const { fps } = useVideoConfig();
  return (
    <TemaCtx.Provider value={roteiro.tema}>
     <VolumeSomCtx.Provider value={roteiro.volumeEfeitos ?? 0.6}>
      <AbsoluteFill style={{ fontFamily: roteiro.tema.fonteTexto }}>
        <Filtros />
        <Fundo />
        <Series>
          {roteiro.blocos.map((b, i) => {
            const d = Math.max(1, Math.round(b.duracao * fps));
            return (
              <Series.Sequence key={b.id} durationInFrames={d} name={`${b.id} · ${b.cena.tipo}`}>
                {i > 0 && <Som tipo="transicao" em={0} volume={0.55} />}
                <BlocoCtx.Provider value={{ palavras: b.palavras ?? [], duracaoFrames: d }}>
                  <Transicao duracaoFrames={d}>
                    <CenaDoBloco bloco={b} duracaoFrames={d} />
                  </Transicao>
                </BlocoCtx.Provider>
              </Series.Sequence>
            );
          })}
        </Series>
        <Marca />
        {roteiro.mostrarLegenda !== false && <Legenda roteiro={roteiro} />}
        <Progresso />
        <Grao />
      </AbsoluteFill>
     </VolumeSomCtx.Provider>
    </TemaCtx.Provider>
  );
};
