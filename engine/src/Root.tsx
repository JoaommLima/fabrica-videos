import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/800.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/700.css';
import '@fontsource/caveat/700.css';
import '@fontsource/nunito/400.css';
import '@fontsource/nunito/700.css';
import '@fontsource/fraunces/800.css';
import '@fontsource/space-grotesk/500.css';
import '@fontsource/space-grotesk/700.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/700.css';
import React from 'react';
import { CalculateMetadataFunction, Composition } from 'remotion';
import { Video } from './Video';
import type { Roteiro } from './types';
import exemplo from '../exemplo-roteiro.json';

export const FPS = 30;

const metadata: CalculateMetadataFunction<Roteiro> = ({ props }) => {
  const total = props.blocos.reduce((s, b) => s + b.duracao, 0);
  return { durationInFrames: Math.max(1, Math.ceil(total * FPS)) };
};

export const RemotionRoot: React.FC = () => (
  <>
    {/* Vídeo longo, horizontal */}
    <Composition
      id="Longo"
      component={Video}
      width={1920}
      height={1080}
      fps={FPS}
      durationInFrames={300}
      defaultProps={exemplo as unknown as Roteiro}
      calculateMetadata={metadata}
    />
    {/* Short vertical: mesmo motor, layout se adapta pela proporção */}
    <Composition
      id="Short"
      component={Video}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={300}
      defaultProps={exemplo as unknown as Roteiro}
      calculateMetadata={metadata}
    />
  </>
);
