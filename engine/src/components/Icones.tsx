import React from 'react';
import type { NoDiagrama } from '../types';

// Ícones genéricos e originais (traço simples), desenhados num viewBox 64x64.
export const Icone: React.FC<{ nome: NoDiagrama['icone']; cor: string; tamanho: number }> = ({ nome, cor, tamanho }) => {
  const p = { fill: 'none', stroke: cor, strokeWidth: 3.2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  let g: React.ReactNode;
  switch (nome) {
    case 'internet':
      g = (
        <>
          <circle cx="32" cy="32" r="22" {...p} />
          <ellipse cx="32" cy="32" rx="10" ry="22" {...p} />
          <path d="M10 32h44M14 20h36M14 44h36" {...p} />
        </>
      );
      break;
    case 'nuvem':
      g = <path d="M20 46h26a10 10 0 0 0 0-20 14 14 0 0 0-27-3A11 11 0 0 0 20 46z" {...p} />;
      break;
    case 'roteador':
      g = (
        <>
          <rect x="8" y="34" width="48" height="16" rx="4" {...p} />
          <path d="M20 34l-6-16M44 34l6-16" {...p} />
          <circle cx="18" cy="42" r="1.8" fill={cor} />
          <circle cx="26" cy="42" r="1.8" fill={cor} />
          <path d="M36 42h12" {...p} />
        </>
      );
      break;
    case 'switch':
      g = (
        <>
          <rect x="6" y="22" width="52" height="20" rx="3" {...p} />
          {[13, 21, 29, 37, 45].map((x) => (
            <rect key={x} x={x} y="28" width="5" height="6" rx="1" fill={cor} />
          ))}
          <path d="M53 29v6" {...p} />
        </>
      );
      break;
    case 'servidor':
      g = (
        <>
          <rect x="12" y="8" width="40" height="14" rx="3" {...p} />
          <rect x="12" y="25" width="40" height="14" rx="3" {...p} />
          <rect x="12" y="42" width="40" height="14" rx="3" {...p} />
          {[15, 32, 49].map((y) => (
            <React.Fragment key={y}>
              <circle cx="20" cy={y} r="1.8" fill={cor} />
              <path d={`M30 ${y}h14`} {...p} />
            </React.Fragment>
          ))}
        </>
      );
      break;
    case 'pc':
      g = (
        <>
          <rect x="8" y="10" width="48" height="32" rx="3" {...p} />
          <path d="M26 54h12M32 42v12" {...p} />
        </>
      );
      break;
    case 'wifi':
      g = (
        <>
          <path d="M10 26a32 32 0 0 1 44 0M17 34a22 22 0 0 1 30 0M24 42a12 12 0 0 1 16 0" {...p} />
          <circle cx="32" cy="50" r="3" fill={cor} />
        </>
      );
      break;
    case 'celular':
      g = (
        <>
          <rect x="20" y="6" width="24" height="52" rx="5" {...p} />
          <path d="M29 50h6" {...p} />
        </>
      );
      break;
    case 'firewall':
      g = (
        <>
          <path d="M32 6l20 8v14c0 14-9 24-20 30C21 52 12 42 12 28V14z" {...p} />
          <path d="M24 32l6 6 11-12" {...p} />
        </>
      );
      break;
    case 'impressora3d':
      g = (
        <>
          <path d="M10 8h44v48H10z" {...p} />
          <path d="M10 18h44M26 18v8h12v-8M32 26v6" {...p} />
          <path d="M22 50h20l-4-10H26z" {...p} />
        </>
      );
      break;
  }
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 64 64">
      {g}
    </svg>
  );
};
