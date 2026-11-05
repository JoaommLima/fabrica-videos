import React from 'react';
import { AbsoluteFill } from 'remotion';
import type { NoDiagrama, Tema } from './types';
import { Icone } from './components/Icones';

export type ThumbProps = {
  tema: Tema;
  variante: 1 | 2 | 3;
  texto: string; // 2 a 5 palavras, grandes
  destaque?: string; // palavra (dentro de `texto`) que ganha a cor de destaque
  apoio?: string; // linha pequena opcional
  selo?: string; // ex.: "HOMELAB"
  icones?: NoDiagrama['icone'][]; // 1 a 3 aparelhos
};

const Grao: React.FC<{ forca: number }> = ({ forca }) =>
  forca ? (
    <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, opacity: forca * 1.4, mixBlendMode: 'overlay' }}>
      <filter id="g">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={3} />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#g)" />
    </svg>
  ) : null;

/** Texto grande com uma palavra destacada (em bloco de cor, que lê bem pequeno no celular). */
const Manchete: React.FC<{ t: Tema; texto: string; destaque?: string; tamanho: number; largura: number }> = ({ t, texto, destaque, tamanho, largura }) => {
  const partes = destaque ? texto.split(new RegExp(`(${destaque.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'i')) : [texto];
  return (
    <div style={{ fontFamily: t.fonteTitulo, fontWeight: 700, fontSize: tamanho, lineHeight: 1.08, letterSpacing: -2, color: t.corTexto, maxWidth: largura, textTransform: 'uppercase' }}>
      {partes.map((p, i) =>
        destaque && p.toLowerCase() === destaque.toLowerCase() ? (
          <span key={i} style={{ background: t.corDestaque, color: t.corSobreDestaque, padding: '2px 14px 0', boxDecorationBreak: 'clone', WebkitBoxDecorationBreak: 'clone' }}>
            {p}
          </span>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </div>
  );
};

const CaixaIcone: React.FC<{ t: Tema; nome: NoDiagrama['icone']; tam: number; cor?: string; giro?: number }> = ({ t, nome, tam, cor, giro = 0 }) => (
  <div
    style={{
      width: tam,
      height: tam,
      background: t.corCartao,
      border: `4px solid ${cor ?? t.corDestaque}`,
      borderRadius: t.raio * 2,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
      transform: `rotate(${giro}deg)`,
    }}
  >
    <Icone nome={nome} cor={cor ?? t.corDestaque} tamanho={tam * 0.62} />
  </div>
);

const Faixa: React.FC<{ t: Tema; style?: React.CSSProperties }> = ({ t, style }) => (
  <div style={{ background: `repeating-linear-gradient(-45deg, ${t.corDestaque} 0 18px, ${t.corFundo} 18px 36px)`, ...style }} />
);

export const Thumb: React.FC<ThumbProps> = ({ tema: t, variante, texto, destaque, apoio, selo, icones = ['switch'] }) => {
  const fundo = `radial-gradient(ellipse at 70% 40%, ${t.corFundo2} 0%, ${t.corFundo} 60%, #000 100%)`;
  const Selo = selo ? (
    <div style={{ display: 'inline-block', fontFamily: t.fonteCodigo, fontWeight: 700, fontSize: 30, color: t.corDestaque, border: `3px solid ${t.corDestaque}`, padding: '6px 16px', marginBottom: 22, letterSpacing: 3 }}>
      {selo}
    </div>
  ) : null;

  if (variante === 2) {
    // Ícone gigante à esquerda, texto à direita
    return (
      <AbsoluteFill style={{ background: fundo }}>
        <div style={{ position: 'absolute', left: 70, top: 130 }}>
          <CaixaIcone t={t} nome={icones[0]} tam={420} giro={-4} />
        </div>
        <div style={{ position: 'absolute', left: 560, right: 60, top: 0, bottom: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {Selo && <div>{Selo}</div>}
          <Manchete t={t} texto={texto} destaque={destaque} tamanho={104} largura={680} />
        </div>
        <Faixa t={t} style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 22 }} />
        <Grao forca={t.granulado} />
      </AbsoluteFill>
    );
  }

  if (variante === 3) {
    // Mini diagrama (aparelhos ligados) + texto em cima — "antes/depois"
    const cores = [t.corDestaque2, t.corDestaque, t.corPerigo];
    return (
      <AbsoluteFill style={{ background: fundo }}>
        <div style={{ position: 'absolute', left: 70, right: 70, top: 60 }}>
          {Selo}
          <Manchete t={t} texto={texto} destaque={destaque} tamanho={112} largura={1140} />
        </div>
        <svg style={{ position: 'absolute', inset: 0 }} width={1280} height={720}>
          {icones.slice(0, 3).map((_, i) => (
            <line key={i} x1={250} y1={560} x2={620 + i * 230} y2={560} stroke={t.corLinha} strokeWidth={5} strokeDasharray="14 10" />
          ))}
        </svg>
        <div style={{ position: 'absolute', left: 150, top: 470 }}>
          <CaixaIcone t={t} nome="roteador" tam={190} cor={t.corTexto} />
        </div>
        {icones.slice(0, 3).map((ic, i) => (
          <div key={i} style={{ position: 'absolute', left: 540 + i * 230, top: 480 }}>
            <CaixaIcone t={t} nome={ic} tam={170} cor={cores[i % 3]} giro={i % 2 ? 3 : -3} />
          </div>
        ))}
        <Grao forca={t.granulado} />
      </AbsoluteFill>
    );
  }

  // Variante 1: texto enorme à esquerda, ícone grande saindo pela direita
  return (
    <AbsoluteFill style={{ background: fundo }}>
      <Faixa t={t} style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 26 }} />
      <div style={{ position: 'absolute', right: -40, top: 140 }}>
        <CaixaIcone t={t} nome={icones[0]} tam={470} giro={6} />
      </div>
      <div style={{ position: 'absolute', left: 80, top: 0, bottom: 0, width: 760, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        {Selo && <div>{Selo}</div>}
        <Manchete t={t} texto={texto} destaque={destaque} tamanho={124} largura={760} />
        {apoio && <div style={{ fontFamily: t.fonteTexto, fontSize: 38, color: t.corSuave, marginTop: 26 }}>{apoio}</div>}
      </div>
      <Grao forca={t.granulado} />
    </AbsoluteFill>
  );
};
