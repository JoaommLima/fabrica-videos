// Formato do roteiro que o pipeline entrega para o motor de cenas.
// Cada bloco = um trecho de narração + a cena que aparece enquanto ele é narrado.

export type NomeEstilo = 'neon' | 'bancada' | 'caderno' | 'revista';

export type Tema = {
  estilo: NomeEstilo;
  nomeCanal: string;
  corFundo: string;
  corFundo2: string;
  corCartao: string;
  corLinha: string;
  corTexto: string;
  corSuave: string;
  corDestaque: string;
  corDestaque2: string;
  corPerigo: string;
  corSobreDestaque: string; // texto em cima da cor de destaque
  fonteTitulo: string;
  pesoTitulo: number;
  fonteTexto: string;
  fonteCodigo: string;
  raio: number;
  borda: number;
  sombra: boolean;
  granulado: number; // 0..0.15 — textura de grão
  rabisco: boolean; // traço "feito à mão"
  maiusculasTitulo: boolean;
};

export type Palavra = { texto: string; inicio: number; fim: number }; // segundos

export type NoDiagrama = {
  id: string;
  rotulo: string;
  icone: 'internet' | 'roteador' | 'switch' | 'servidor' | 'pc' | 'wifi' | 'celular' | 'nuvem' | 'firewall' | 'impressora3d';
  x: number; // 0..100 (% da área do diagrama)
  y: number; // 0..100
  grupo?: string; // nós do mesmo grupo ganham a mesma cor (ex.: VLAN)
};

/**
 * `gatilhos` (opcional, em qualquer cena com itens): palavra da narração que faz cada item aparecer.
 * Sem isso, o motor procura sozinho na fala a primeira palavra parecida com o texto do item.
 */
export type Cena =
  | { tipo: 'abertura'; titulo: string; subtitulo?: string; selo?: string }
  | { tipo: 'lista'; titulo: string; itens: string[]; gatilhos?: string[] }
  | { tipo: 'diagrama'; titulo?: string; nos: NoDiagrama[]; ligacoes: [string, string][]; pacote?: string[]; grupos?: Record<string, string>; gatilhos?: string[] }
  | { tipo: 'terminal'; titulo?: string; prompt?: string; linhas: { cmd?: string; saida?: string }[] }
  | { tipo: 'comparacao'; titulo?: string; esquerda: { titulo: string; itens: string[] }; direita: { titulo: string; itens: string[] } }
  | { tipo: 'numero'; valor: number; prefixo?: string; sufixo?: string; legenda: string; casas?: number }
  | { tipo: 'frase'; texto: string; autor?: string }
  | { tipo: 'linha-do-tempo'; titulo?: string; marcos: { ano: string; texto: string }[]; gatilhos?: string[] }
  | { tipo: 'encerramento'; titulo: string; texto?: string };

export type Bloco = {
  id: string;
  narracao: string;
  duracao: number; // segundos (vem do áudio real; no rascunho é estimado)
  palavras?: Palavra[]; // tempos das palavras DENTRO do bloco (0 = início do bloco)
  cena: Cena;
};

export type Roteiro = {
  titulo: string;
  tema: Tema;
  blocos: Bloco[];
  legendas?: Palavra[];
  mostrarLegenda?: boolean;
  volumeEfeitos?: number; // 0 desliga os efeitos sonoros
};
