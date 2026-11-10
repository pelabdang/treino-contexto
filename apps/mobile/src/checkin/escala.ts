// Escalas e textos fixos do check-in pós-treino (ADR 0012, itens 2 e 3; spec docs/design/telas/checkin.md).
// Tudo que o Angelo pode mudar (prazo, campos obrigatórios) fica aqui, num lugar só.
import type { AtalhoCheckin, CheckinEnvio } from "@treino/api-client";

/** Prazo padrão para criar o check-in (A confirmar 1 da ADR 0012). Só aparece em texto: quem decide é `checkin_aberto`. */
export const PRAZO_DIAS = 7;

/** Rótulos fixos da escala CR-10 (ADR 0012, item 2). 6, 8 e 9 ficam sem âncora. */
export const ANCORAS_PSE: Record<number, string | null> = {
  0: "repouso",
  1: "muito leve",
  2: "leve",
  3: "moderado",
  4: "um pouco difícil",
  5: "difícil",
  6: null,
  7: "muito difícil",
  8: null,
  9: null,
  10: "máximo",
};
export const NIVEIS_PSE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const;

export type IconeSensacao =
  | "sentiment-very-dissatisfied"
  | "sentiment-dissatisfied"
  | "sentiment-neutral"
  | "sentiment-satisfied"
  | "sentiment-very-satisfied";

export const SENSACOES: { valor: number; texto: string; icone: IconeSensacao }[] = [
  { valor: 1, texto: "Muito mal", icone: "sentiment-very-dissatisfied" },
  { valor: 2, texto: "Mal", icone: "sentiment-dissatisfied" },
  { valor: 3, texto: "Normal", icone: "sentiment-neutral" },
  { valor: 4, texto: "Bem", icone: "sentiment-satisfied" },
  { valor: 5, texto: "Muito bem", icone: "sentiment-very-satisfied" },
];

export type ChaveAtalho = AtalhoCheckin["chave"];

export const ATALHOS: { chave: ChaveAtalho; texto: string }[] = [
  { chave: "dor", texto: "Dor" },
  { chave: "cansaco", texto: "Cansaço" },
  { chave: "sono_ruim", texto: "Sono ruim" },
  { chave: "calor", texto: "Calor" },
  { chave: "trabalho_estresse", texto: "Trabalho ou estresse" },
];

export const LIMITE_TEXTO = 500;
export const AVISO_TEXTO = 450;

/** "5 · difícil" ou só "6". */
export function pseComAncora(pse: number): string {
  const a = ANCORAS_PSE[pse] ?? null;
  return a ? `${pse} · ${a}` : String(pse);
}

/** Leitor de tela: "PSE 5, difícil" ou "PSE 6". */
export function pseFalada(pse: number): string {
  const a = ANCORAS_PSE[pse] ?? null;
  return a ? `PSE ${pse}, ${a}` : `PSE ${pse}`;
}

/** "Na parte anterior você marcou 5 (difícil)." ou, sem âncora, "Na parte anterior você marcou 6.". */
export function avisoPseSugerida(pse: number): string {
  const a = ANCORAS_PSE[pse] ?? null;
  return a ? `Na parte anterior você marcou ${pse} (${a}).` : `Na parte anterior você marcou ${pse}.`;
}

export type Observacao = { nadaARelatar: boolean; atalhos: ChaveAtalho[]; texto: string };

/** A observação só vale com uma escolha explícita: "nada a relatar", um atalho ou texto (ADR 0012, item 1). */
export function observacaoValida(o: Observacao): boolean {
  return o.nadaARelatar || o.atalhos.length > 0 || o.texto.trim().length > 0;
}

/** Os três campos são obrigatórios (A confirmar 3 da ADR 0012): é aqui que isso mudaria. */
export function checkinCompleto(pse: number | null, sensacao: number | null, o: Observacao): boolean {
  return pse !== null && sensacao !== null && observacaoValida(o);
}

export function temConteudoSensivel(o: Observacao): boolean {
  return o.atalhos.length > 0 || o.texto.trim().length > 0;
}

export function montarEnvio(pse: number, sensacao: number, o: Observacao): CheckinEnvio {
  if (o.nadaARelatar) return { pse, sensacao, nada_a_relatar: true, atalhos: [], texto: null };
  const texto = o.texto.trim();
  return {
    pse,
    sensacao,
    nada_a_relatar: false,
    // ordem fixa da lista, não a ordem dos toques
    atalhos: ATALHOS.map((a) => a.chave).filter((c) => o.atalhos.includes(c)),
    texto: texto.length > 0 ? texto : null,
  };
}

/** "5 · difícil" com o `pse_texto` que a API mandou; sem âncora (ou igual ao número), só o número. */
export function pseDoCheckin(c: { pse: number; pse_texto: string }): string {
  return c.pse_texto && c.pse_texto !== String(c.pse) ? `${c.pse} · ${c.pse_texto}` : String(c.pse);
}

/** Observação em duas partes: a linha (atalhos ou "Nada a relatar") e o texto livre, quando houver. */
export function observacaoDoCheckin(c: { nada_a_relatar: boolean; atalhos: { texto: string }[]; texto: string | null }): {
  linha: string;
  texto: string | null;
} {
  if (c.nada_a_relatar) return { linha: "Nada a relatar", texto: null };
  return { linha: c.atalhos.map((a) => a.texto).join(", "), texto: c.texto };
}

export const textoForaDoPrazo = () =>
  `O prazo para fazer o check-in deste treino acabou (${PRAZO_DIAS} dias depois do treino). Check-ins que já existem ainda podem ser editados.`;
export const avisoPrazoNoCartao = () => `O prazo para fazer o check-in deste treino acabou (${PRAZO_DIAS} dias depois do treino).`;
export const TEXTO_SEM_CHECKIN_ELEGIVEL = "Este treino não pede check-in.";
