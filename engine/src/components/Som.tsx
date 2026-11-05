import React, { createContext, useContext } from 'react';
import { Audio, Sequence, staticFile } from 'remotion';

/** Efeitos sonoros (engine/public/sfx, gerados por pipeline/gerar_sons.py). */
export type TipoSom = 'pop' | 'whoosh' | 'transicao' | 'tecla1' | 'tecla2' | 'tecla3' | 'tick' | 'ding' | 'clique';

const DURACAO: Record<TipoSom, number> = { pop: 6, whoosh: 15, transicao: 11, tecla1: 3, tecla2: 3, tecla3: 3, tick: 3, ding: 30, clique: 4 };

/** Volume geral dos efeitos (0 desliga). Vem de canal/config.json → audio.volumeEfeitos. */
export const VolumeSomCtx = createContext(0.6);

export const Som: React.FC<{ tipo: TipoSom; em: number; volume?: number }> = ({ tipo, em, volume = 1 }) => {
  const geral = useContext(VolumeSomCtx);
  if (geral <= 0 || em < 0) return null;
  return (
    <Sequence from={Math.round(em)} durationInFrames={DURACAO[tipo]} layout="none" name={`som ${tipo}`}>
      <Audio src={staticFile(`sfx/${tipo}.wav`)} volume={Math.min(1, geral * volume)} />
    </Sequence>
  );
};
