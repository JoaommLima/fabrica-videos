import React, { createContext, useContext } from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig, Easing } from 'remotion';
import type { Tema } from '../types';

export const TemaCtx = createContext<Tema | null>(null);
export const useTema = () => {
  const t = useContext(TemaCtx);
  if (!t) throw new Error('Tema ausente');
  return t;
};

/** u = unidade base (1px em 1080p). vertical = Short 9:16. */
export const useLayout = () => {
  const { width, height } = useVideoConfig();
  const u = Math.min(width, height) / 1080;
  return { u, vertical: height > width, width, height };
};

/** Entrada suave (0→1) começando no frame `atraso`. */
export const useEntrada = (atraso = 0, damping = 18) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - atraso, fps, config: { damping, mass: 0.7 } });
};

export const Surge: React.FC<{ atraso?: number; de?: 'baixo' | 'esquerda' | 'direita' | 'zoom'; children: React.ReactNode; style?: React.CSSProperties }> = ({
  atraso = 0,
  de = 'baixo',
  children,
  style,
}) => {
  const p = useEntrada(atraso);
  const { u } = useLayout();
  const d = (1 - p) * 40 * u;
  const transform =
    de === 'baixo' ? `translateY(${d}px)` : de === 'esquerda' ? `translateX(${-d}px)` : de === 'direita' ? `translateX(${d}px)` : `scale(${0.85 + 0.15 * p})`;
  return <div style={{ opacity: p, transform, ...style }}>{children}</div>;
};

/** Envolve cada cena: fade/slide na entrada e na saída. */
export const Transicao: React.FC<{ duracaoFrames: number; children: React.ReactNode }> = ({ duracaoFrames, children }) => {
  const frame = useCurrentFrame();
  const t = 9;
  const entrada = interpolate(frame, [0, t], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
  const saida = interpolate(frame, [duracaoFrames - t, duracaoFrames], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic) });
  const o = Math.min(entrada, saida);
  return <div style={{ position: 'absolute', inset: 0, opacity: o, transform: `scale(${0.985 + 0.015 * o})` }}>{children}</div>;
};

export const Titulo: React.FC<{ children: React.ReactNode; tamanho?: number; atraso?: number }> = ({ children, tamanho = 64, atraso = 0 }) => {
  const tema = useTema();
  const { u } = useLayout();
  return (
    <Surge atraso={atraso}>
      <div style={{ fontFamily: tema.fonteTexto, fontWeight: 800, fontSize: tamanho * u, color: tema.corTexto, letterSpacing: -1.5 * u, lineHeight: 1.08 }}>
        {children}
      </div>
    </Surge>
  );
};

/** Barra de destaque abaixo de títulos. */
export const Sublinhado: React.FC<{ atraso?: number }> = ({ atraso = 6 }) => {
  const tema = useTema();
  const { u } = useLayout();
  const p = useEntrada(atraso, 24);
  return <div style={{ width: 120 * u * p, height: 8 * u, borderRadius: 4 * u, background: tema.corDestaque, marginTop: 22 * u }} />;
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
