import React, { createContext, useContext } from 'react';
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Palavra, Tema } from '../types';

// ───────────────────────── contextos ─────────────────────────
export const TemaCtx = createContext<Tema | null>(null);
export const useTema = () => {
  const t = useContext(TemaCtx);
  if (!t) throw new Error('Tema ausente');
  return t;
};

type InfoBloco = { palavras: Palavra[]; duracaoFrames: number };
export const BlocoCtx = createContext<InfoBloco>({ palavras: [], duracaoFrames: 1 });

/** u = unidade base (1px em 1080p). vertical = Short 9:16. */
export const useLayout = () => {
  const { width, height } = useVideoConfig();
  const u = Math.min(width, height) / 1080;
  return { u, vertical: height > width, width, height };
};

export const useEntrada = (atraso = 0, damping = 18) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - atraso, fps, config: { damping, mass: 0.7 } });
};

// ───────────────────────── sincronia com a fala ─────────────────────────
const PARADAS = new Set(
  'a o e as os um uma de da do das dos em no na nos nas por para com sem que se ao aos é são ser sua seu suas seus mais muito só isso esse essa este esta the'.split(' '),
);
const norm = (s: string) =>
  s
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9 ]/g, ' ')
    .split(/\s+/)
    .filter(Boolean);
const casa = (a: string, b: string) => {
  const n = Math.min(5, a.length, b.length);
  return n >= 3 && a.slice(0, n) === b.slice(0, n);
};

/**
 * Frame em que cada item deve aparecer: quando a narração fala a palavra correspondente.
 * Procura em ordem (um item nunca aparece antes do anterior). Sem correspondência,
 * usa o ritmo padrão logo depois do item anterior.
 */
export const useGatilhos = (textos: string[], explicitos?: string[], inicio = 18, passoPadrao = 24): number[] => {
  const { palavras } = useContext(BlocoCtx);
  const { fps } = useVideoConfig();
  const fala = palavras.map((p) => ({ n: norm(p.texto)[0] ?? '', t: p.inicio }));
  let cursor = 0;
  let ultimo = inicio - passoPadrao;
  return textos.map((txt, i) => {
    const alvo = norm(explicitos?.[i] ?? txt).filter((w) => !PARADAS.has(w) && w.length >= 3);
    let achou: number | null = null;
    for (let k = cursor; k < fala.length && achou === null; k++) {
      if (alvo.some((w) => casa(w, fala[k].n))) {
        achou = Math.round(fala[k].t * fps) - 4; // aparece um tiquinho antes da palavra
        cursor = k + 1;
      }
    }
    const f = Math.max(achou ?? ultimo + passoPadrao, ultimo + 6, 6);
    ultimo = f;
    return f;
  });
};

// ───────────────────────── entrada de elementos ─────────────────────────
export const Surge: React.FC<{ atraso?: number; de?: 'baixo' | 'esquerda' | 'direita' | 'zoom'; children: React.ReactNode; style?: React.CSSProperties }> = ({
  atraso = 0,
  de = 'baixo',
  children,
  style,
}) => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const p = useEntrada(atraso);
  const { u } = useLayout();

  if (tema.estilo === 'revista') {
    // máscara que "abre" de baixo pra cima, sem fade — mais editorial
    const q = interpolate(frame - atraso, [0, 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.exp) });
    return <div style={{ clipPath: `inset(${(1 - q) * 100}% 0 0 0)`, transform: `translateY(${(1 - q) * 30 * u}px)`, ...style }}>{children}</div>;
  }
  if (tema.estilo === 'bancada') {
    // corte lateral, como etiqueta sendo puxada
    const q = interpolate(frame - atraso, [0, 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
    return <div style={{ clipPath: `inset(0 ${(1 - q) * 100}% 0 0)`, opacity: Math.min(1, q * 3), ...style }}>{children}</div>;
  }
  if (tema.estilo === 'caderno') {
    // "cai" no papel com uma leve inclinação, como um post-it
    const giro = (1 - p) * (atraso % 2 ? -3 : 3);
    return <div style={{ opacity: p, transform: `translateY(${(1 - p) * 18 * u}px) rotate(${giro}deg) scale(${0.96 + 0.04 * p})`, ...style }}>{children}</div>;
  }
  const d = (1 - p) * 40 * u;
  const transform =
    de === 'baixo' ? `translateY(${d}px)` : de === 'esquerda' ? `translateX(${-d}px)` : de === 'direita' ? `translateX(${d}px)` : `scale(${0.85 + 0.15 * p})`;
  return <div style={{ opacity: p, transform, ...style }}>{children}</div>;
};

/** Envolve cada cena: entrada/saída + "câmera" que aproxima devagar. */
export const Transicao: React.FC<{ duracaoFrames: number; children: React.ReactNode }> = ({ duracaoFrames, children }) => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const t = tema.estilo === 'revista' ? 4 : 9;
  const entrada = interpolate(frame, [0, t], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
  const saida = interpolate(frame, [duracaoFrames - t, duracaoFrames], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic) });
  const o = Math.min(entrada, saida);
  const camera = interpolate(frame, [0, duracaoFrames], [1, 1.035]);
  const deriva = interpolate(frame, [0, duracaoFrames], [0, -8]);
  return (
    <div style={{ position: 'absolute', inset: 0, opacity: o, transform: `scale(${camera}) translateX(${deriva}px)`, transformOrigin: '45% 45%' }}>{children}</div>
  );
};

// ───────────────────────── tipografia ─────────────────────────
export const Titulo: React.FC<{ children: React.ReactNode; tamanho?: number; atraso?: number; centro?: boolean }> = ({ children, tamanho = 64, atraso = 0, centro }) => {
  const tema = useTema();
  const { u } = useLayout();
  const marca = useEntrada(atraso + 8, 26);
  const escala = tema.estilo === 'caderno' ? 1.35 : tema.estilo === 'revista' ? 1.12 : 1;
  const base: React.CSSProperties = {
    fontFamily: tema.fonteTitulo,
    fontWeight: tema.pesoTitulo,
    fontSize: tamanho * escala * u,
    color: tema.corTexto,
    letterSpacing: (tema.estilo === 'caderno' ? 0 : tema.estilo === 'revista' ? -2 : -1.5) * u,
    lineHeight: tema.estilo === 'caderno' ? 1.0 : 1.06,
    position: 'relative',
    display: 'inline-block',
  };
  return (
    <Surge atraso={atraso}>
      <div style={{ textAlign: centro ? 'center' : 'left' }}>
        {tema.estilo === 'bancada' && (
          <div style={{ fontFamily: tema.fonteCodigo, fontSize: 24 * u, color: tema.corDestaque, letterSpacing: 2 * u, marginBottom: 10 * u }}>// {tema.nomeCanal.toUpperCase()}</div>
        )}
        <div style={base}>
          {tema.estilo === 'caderno' && (
            // marca-texto passando por trás do título
            <div
              style={{
                position: 'absolute',
                left: -12 * u,
                bottom: 6 * u,
                height: '42%',
                width: `calc(${marca * 100}% + ${24 * u}px)`,
                background: tema.corDestaque,
                opacity: 0.85,
                borderRadius: 6 * u,
                transform: 'skewX(-8deg) rotate(-1deg)',
                zIndex: 0,
              }}
            />
          )}
          <span style={{ position: 'relative', zIndex: 1 }}>{children}</span>
          {tema.estilo === 'revista' && typeof children === 'string' && !/[.!?:]$/.test(children.trim()) && <span style={{ color: tema.corDestaque }}>.</span>}
        </div>
      </div>
    </Surge>
  );
};

export const Sublinhado: React.FC<{ atraso?: number }> = ({ atraso = 6 }) => {
  const tema = useTema();
  const { u } = useLayout();
  const p = useEntrada(atraso, 24);
  if (tema.estilo === 'caderno') {
    const L = 260;
    return (
      <svg width={L * u} height={30 * u} viewBox={`0 0 ${L} 30`} style={{ marginTop: 6 * u, overflow: 'visible' }}>
        <path
          d="M2 18 C 40 6, 80 26, 120 14 S 200 8, 256 16"
          fill="none"
          stroke={tema.corPerigo}
          strokeWidth={5}
          strokeLinecap="round"
          strokeDasharray={300}
          strokeDashoffset={300 * (1 - p)}
          filter="url(#rabisco)"
        />
      </svg>
    );
  }
  if (tema.estilo === 'revista') {
    return <div style={{ width: `${p * 100}%`, height: 4 * u, background: tema.corLinha, marginTop: 26 * u }} />;
  }
  if (tema.estilo === 'bancada') {
    return (
      <div
        style={{
          width: 180 * u * p,
          height: 12 * u,
          marginTop: 22 * u,
          background: `repeating-linear-gradient(-45deg, ${tema.corDestaque} 0 ${10 * u}px, ${tema.corFundo} ${10 * u}px ${20 * u}px)`,
        }}
      />
    );
  }
  return <div style={{ width: 120 * u * p, height: 8 * u, borderRadius: 4 * u, background: tema.corDestaque, marginTop: 22 * u }} />;
};

/** Cartão/caixa no estilo do canal. */
export const Cartao: React.FC<{ children?: React.ReactNode; cor?: string; style?: React.CSSProperties; topo?: string }> = ({ children, cor, style, topo }) => {
  const tema = useTema();
  const { u } = useLayout();
  const linha = cor ?? (tema.estilo === 'neon' ? 'rgba(255,255,255,0.12)' : tema.corLinha);
  return (
    <div
      style={{
        position: 'relative',
        background: tema.corCartao,
        borderRadius: tema.raio * u,
        boxShadow: tema.sombra ? `0 ${10 * u}px ${30 * u}px rgba(0,0,0,0.35)` : tema.estilo === 'revista' ? `${8 * u}px ${8 * u}px 0 ${tema.corLinha}` : undefined,
        ...style,
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: tema.raio * u,
          border: `${tema.borda * u}px solid ${linha}`,
          borderTop: topo ? `${8 * u}px solid ${topo}` : undefined,
          filter: tema.rabisco ? 'url(#rabisco)' : undefined,
          pointerEvents: 'none',
        }}
      />
      <div style={{ position: 'relative' }}>{children}</div>
    </div>
  );
};

/** Container de cena com margens seguras. */
export const Palco: React.FC<{ children: React.ReactNode; centro?: boolean; style?: React.CSSProperties }> = ({ children, centro, style }) => {
  const { u, vertical } = useLayout();
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        padding: vertical ? `${260 * u}px ${70 * u}px ${420 * u}px` : `${110 * u}px ${150 * u}px ${170 * u}px`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: centro ? 'center' : 'flex-start',
        alignItems: centro ? 'center' : 'stretch',
        textAlign: centro ? 'center' : 'left',
        ...style,
      }}
    >
      {children}
    </div>
  );
};

// ───────────────────────── fundo, textura e filtros ─────────────────────────
export const Filtros: React.FC = () => {
  const frame = useCurrentFrame();
  const semente = Math.floor(frame / 5) % 4; // traço "fervendo" de leve, como desenho animado à mão
  return (
    <svg width={0} height={0} style={{ position: 'absolute' }}>
      <filter id="rabisco" filterUnits="userSpaceOnUse" x={-200} y={-200} width={5000} height={5000}>
        <feTurbulence type="fractalNoise" baseFrequency="0.025" numOctaves={2} seed={semente} result="r" />
        <feDisplacementMap in="SourceGraphic" in2="r" scale={3.5} />
      </filter>
    </svg>
  );
};

export const Fundo: React.FC = () => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { u, vertical } = useLayout();
  if (tema.estilo === 'caderno') {
    const g = 44 * u;
    return (
      <AbsoluteFill style={{ background: tema.corFundo }}>
        <AbsoluteFill style={{ backgroundImage: `radial-gradient(${tema.corLinha}33 ${1.6 * u}px, transparent ${1.8 * u}px)`, backgroundSize: `${g}px ${g}px` }} />
        <div style={{ position: 'absolute', top: 0, bottom: 0, left: (vertical ? 46 : 110) * u, width: 3 * u, background: '#e8838366' }} />
      </AbsoluteFill>
    );
  }
  if (tema.estilo === 'bancada') {
    return <AbsoluteFill style={{ background: `radial-gradient(ellipse at 35% 30%, ${tema.corFundo2} 0%, ${tema.corFundo} 65%, #0c0a08 100%)` }} />;
  }
  if (tema.estilo === 'revista') {
    return <AbsoluteFill style={{ background: tema.corFundo }} />;
  }
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

/** Grão de filme por cima de tudo (tira a "cara de digital limpo demais"). */
export const Grao: React.FC = () => {
  const tema = useTema();
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  if (!tema.granulado) return null;
  return (
    <svg width={width} height={height} style={{ position: 'absolute', inset: 0, opacity: tema.granulado, mixBlendMode: 'overlay', pointerEvents: 'none' }}>
      <filter id="grao">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={frame % 30} stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grao)" />
    </svg>
  );
};
