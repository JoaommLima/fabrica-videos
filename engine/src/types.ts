// Formato do roteiro que o pipeline entrega para o motor de cenas.
// Cada bloco = um trecho de narração + a cena que aparece enquanto ele é narrado.

export type Tema = {
  nomeCanal: string;
  corFundo: string;
  corFundo2: string;
  corTexto: string;
  corSuave: string;
  corDestaque: string;
  corDestaque2: string;
  corPerigo: string;
  fonteTexto: string;
  fonteCodigo: string;
};

export type Palavra = { texto: string; inicio: number; fim: number }; // segundos, relativos ao vídeo

export type NoDiagrama = {
  id: string;
  rotulo: string;
  icone: 'internet' | 'roteador' | 'switch' | 'servidor' | 'pc' | 'wifi' | 'celular' | 'nuvem' | 'firewall' | 'impressora3d';
  x: number; // 0..100 (% da área do diagrama)
  y: number; // 0..100
  grupo?: string; // nós do mesmo grupo ganham a mesma cor (ex.: VLAN)
};

export type Cena =
  | { tipo: 'abertura'; titulo: string; subtitulo?: string; selo?: string }
  | { tipo: 'lista'; titulo: string; itens: string[] }
  | { tipo: 'diagrama'; titulo?: string; nos: NoDiagrama[]; ligacoes: [string, string][]; pacote?: string[]; grupos?: Record<string, string> }
  | { tipo: 'terminal'; titulo?: string; prompt?: string; linhas: { cmd?: string; saida?: string }[] }
  | { tipo: 'comparacao'; titulo?: string; esquerda: { titulo: string; itens: string[] }; direita: { titulo: string; itens: string[] } }
  | { tipo: 'numero'; valor: number; prefixo?: string; sufixo?: string; legenda: string; casas?: number }
  | { tipo: 'frase'; texto: string; autor?: string }
  | { tipo: 'linha-do-tempo'; titulo?: string; marcos: { ano: string; texto: string }[] }
  | { tipo: 'encerramento'; titulo: string; texto?: string };

export type Bloco = {
  id: string;
  narracao: string;
  duracao: number; // segundos (vem do áudio real; no rascunho é estimado)
  cena: Cena;
};

export type Roteiro = {
  titulo: string;
  tema: Tema;
  blocos: Bloco[];
  legendas?: Palavra[];
  mostrarLegenda?: boolean;
};
