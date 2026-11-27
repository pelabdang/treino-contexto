// Onde o app guarda o acesso (ADR 0016, item 3; decisão 1 do Theo): no celular, o cofre do aparelho (expo-secure-store); na web,
// `sessionStorage` (morre ao fechar a aba). Só o token e o endereço lembrado; nunca e-mail, senha nem dado de treino.
// Nunca lança: sem armazenamento, lê `null` e não grava nada (o app pede o login de novo).
import { Platform } from "react-native";

const CHAVE_TOKEN = "treino.acesso";
const CHAVE_DESTINO = "treino.destino";

type Cofre = {
  getItemAsync: (k: string) => Promise<string | null>;
  setItemAsync: (k: string, v: string) => Promise<void>;
  deleteItemAsync: (k: string) => Promise<void>;
};

// Carregado só no celular: o módulo nativo não existe na web.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const cofre = (): Cofre => require("expo-secure-store") as Cofre;

async function ler(chave: string): Promise<string | null> {
  try {
    if (Platform.OS === "web") return globalThis.sessionStorage?.getItem(chave) ?? null;
    return await cofre().getItemAsync(chave);
  } catch {
    return null;
  }
}

async function gravar(chave: string, valor: string): Promise<void> {
  try {
    if (Platform.OS === "web") globalThis.sessionStorage?.setItem(chave, valor);
    else await cofre().setItemAsync(chave, valor);
  } catch {
    // sem armazenamento: o acesso vale só até fechar o app
  }
}

async function apagar(chave: string): Promise<void> {
  try {
    if (Platform.OS === "web") globalThis.sessionStorage?.removeItem(chave);
    else await cofre().deleteItemAsync(chave);
  } catch {
    // nada a apagar
  }
}

export const lerToken = () => ler(CHAVE_TOKEN);
export const gravarToken = (t: string) => gravar(CHAVE_TOKEN, t);
export const lerDestino = () => ler(CHAVE_DESTINO);
export const gravarDestino = (d: string) => gravar(CHAVE_DESTINO, d);
export const apagarDestino = () => apagar(CHAVE_DESTINO);
/** Sair: apaga o token e o endereço lembrado. Acesso expirado: `manterDestino` apaga só o token. */
export async function apagarTudo(manterDestino = false): Promise<void> {
  await apagar(CHAVE_TOKEN);
  if (!manterDestino) await apagar(CHAVE_DESTINO);
}

// Preferência de tela (não é acesso): a última série da Evolução. No celular, o cofre; na web, `localStorage` (sobrevive à aba).
// Só o id da série (texto do catálogo), nunca dado de treino. Nunca lança.
const chaveSerie = (atletaId: number) => `treino.evolucao.serie.${atletaId}`;

export async function lerUltimaSerie(atletaId: number): Promise<string | null> {
  try {
    if (Platform.OS === "web") return globalThis.localStorage?.getItem(chaveSerie(atletaId)) ?? null;
    return await cofre().getItemAsync(chaveSerie(atletaId));
  } catch {
    return null;
  }
}

export async function gravarUltimaSerie(atletaId: number, serieId: string): Promise<void> {
  try {
    if (Platform.OS === "web") globalThis.localStorage?.setItem(chaveSerie(atletaId), serieId);
    else await cofre().setItemAsync(chaveSerie(atletaId), serieId);
  } catch {
    // sem armazenamento: na próxima vez abre na série padrão
  }
}
