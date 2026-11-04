// Tokens do guia visual. Fonte única: docs/design/tokens.md (a tabela "Cores" é
// conferida por __tests__/tema.test.ts). Mesmos nomes do guia, sem o prefixo "cor.".

export const coresClaro = {
  fundo: "#F6F5F1",
  superficie: "#FFFFFF",
  "superficie-2": "#ECEAE4",
  borda: "#DEDBD3",
  "borda-forte": "#7D7A72",
  texto: "#1A1D1F",
  "texto-2": "#4C5257",
  "texto-desligado": "#9A9890",
  destaque: "#0B6A6E",
  "destaque-pressionado": "#08514F",
  "sobre-destaque": "#FFFFFF",
  "destaque-suave": "#DCEFEE",
  foco: "#0B6A6E",
  sucesso: "#1B6E3A",
  "sucesso-suave": "#E3F2E8",
  alerta: "#8A5300",
  "alerta-suave": "#FCEFD6",
  erro: "#B3261E",
  "erro-suave": "#FBE6E4",
  corrida: "#B4470F",
  ciclismo: "#6B3FB0",
  natacao: "#1A5FA8",
  "grafico.pace": "#3340B0",
  "grafico.fc": "#A3205F",
  "grafico.media": "#6B7176",
  "grafico.grade": "#E3E1DA",
  "bloco.esforco": "#1A1D1F",
  "bloco.recuperacao": "#8C8981",
  "bloco.aquecimento": "#8C8981",
  "bloco.leve": "#8C8981",
} as const;

export type NomeCor = keyof typeof coresClaro;
export type Cores = Record<NomeCor, string>;

export const coresEscuro: Cores = {
  fundo: "#121517",
  superficie: "#1C2023",
  "superficie-2": "#262B2F",
  borda: "#33393E",
  "borda-forte": "#80878D",
  texto: "#ECEEEF",
  "texto-2": "#B4BBC0",
  "texto-desligado": "#5E656A",
  destaque: "#5CC8C4",
  "destaque-pressionado": "#86DAD6",
  "sobre-destaque": "#0B1A1B",
  "destaque-suave": "#163536",
  foco: "#5CC8C4",
  sucesso: "#6FD08E",
  "sucesso-suave": "#17301F",
  alerta: "#F2B851",
  "alerta-suave": "#3A2C12",
  erro: "#FF8A80",
  "erro-suave": "#3D1C1A",
  corrida: "#FF9A5C",
  ciclismo: "#BFA2F2",
  natacao: "#7DB7F0",
  "grafico.pace": "#9AA4F5",
  "grafico.fc": "#F48FBF",
  "grafico.media": "#8E969C",
  "grafico.grade": "#2C3236",
  "bloco.esforco": "#ECEEEF",
  "bloco.recuperacao": "#7A8186",
  "bloco.aquecimento": "#7A8186",
  "bloco.leve": "#7A8186",
};

export const cores: { claro: Cores; escuro: Cores } = { claro: coresClaro, escuro: coresEscuro };

export const espaco = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32, 7: 48 } as const;
export const larguraConteudoMax = 720;

export const raio = { pequeno: 4, medio: 8, grande: 12, pilula: 999 } as const;
export const borda = { fina: 1, foco: 2 } as const;

export const tamanho = {
  alvoMinimo: 44,
  botaoAltura: 48,
  iconePequeno: 16,
  iconeMedio: 20,
  iconeGrande: 24,
  iconeEstado: 40,
  graficoLinhaPrincipal: 2,
  graficoLinhaMedia: 1.5,
  graficoPontoRaio: 5,
  graficoPontoSelecionadoRaio: 7,
  graficoPainelAltura: 160,
} as const;

export const movimento = { rapido: 150, esqueleto: 1200 } as const;

// Pesos da Inter (nomes das fontes do @expo-google-fonts/inter).
export const familia = {
  regular: "Inter_400Regular",
  medio: "Inter_500Medium",
  semibold: "Inter_600SemiBold",
  bold: "Inter_700Bold",
} as const;

type Fonte = {
  fontFamily: string;
  fontSize: number;
  lineHeight: number;
  fontVariant?: ["tabular-nums"];
  maxFontSizeMultiplier?: number;
};

export const fonte = {
  "numero-destaque": { fontFamily: familia.bold, fontSize: 40, lineHeight: 44, fontVariant: ["tabular-nums"], maxFontSizeMultiplier: 1.5 },
  "titulo-tela": { fontFamily: familia.bold, fontSize: 24, lineHeight: 30, maxFontSizeMultiplier: 1.5 },
  "titulo-secao": { fontFamily: familia.semibold, fontSize: 18, lineHeight: 24 },
  corpo: { fontFamily: familia.regular, fontSize: 16, lineHeight: 24 },
  "corpo-forte": { fontFamily: familia.semibold, fontSize: 16, lineHeight: 24 },
  botao: { fontFamily: familia.semibold, fontSize: 16, lineHeight: 20 },
  rotulo: { fontFamily: familia.medio, fontSize: 14, lineHeight: 20 },
  legenda: { fontFamily: familia.regular, fontSize: 13, lineHeight: 18 },
  eixo: { fontFamily: familia.medio, fontSize: 12, lineHeight: 16, fontVariant: ["tabular-nums"] },
} satisfies Record<string, Fonte>;

export type NomeFonte = keyof typeof fonte;
