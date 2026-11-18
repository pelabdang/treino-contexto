// Consentimento do atleta e termo (#503, ADR 0016, item 7). Tipos do cliente gerado; funções aqui, como no check-in. Nunca lançam.
// Privacidade: nome do professor, versão do termo e o fato de ter consentido NUNCA vão para log, console nem mensagem de erro.
import type { components, OpcoesCliente, Resultado } from "@treino/api-client";

import { chamar } from "../checkin/api";

export type Vinculo = components["schemas"]["VinculoOut"];
export type Professores = components["schemas"]["ProfessoresOut"];
export type Termo = components["schemas"]["TermoOut"];

const atleta = (id: number) => `/atletas/${encodeURIComponent(String(id))}/professores`;
const json = { Accept: "application/json" };

/** `GET /atletas/{id}/professores`: vínculos com `consentimento` ativo ou não. */
export const buscarProfessores = (atletaId: number, opcoes: OpcoesCliente = {}): Promise<Resultado<Professores>> =>
  chamar<Professores>(atleta(atletaId), { headers: json }, opcoes);

/** `GET /termo-de-consentimento`: versão, texto e `provisorio`. */
export const buscarTermo = (opcoes: OpcoesCliente = {}): Promise<Resultado<Termo>> =>
  chamar<Termo>("/termo-de-consentimento", { headers: json }, opcoes);

/** `PUT .../consentimento` com a versão lida. 409: o termo mudou; 404: o vínculo não existe mais. */
export const darConsentimento = (atletaId: number, professorId: number, termoVersao: string, opcoes: OpcoesCliente = {}): Promise<Resultado<Vinculo>> =>
  chamar<Vinculo>(
    `${atleta(atletaId)}/${encodeURIComponent(String(professorId))}/consentimento`,
    { method: "PUT", headers: { ...json, "Content-Type": "application/json" }, body: JSON.stringify({ termo_versao: termoVersao }) },
    opcoes,
  );

/** `DELETE .../consentimento` (204): o vínculo fica e volta a "aguardando". */
export const retirarConsentimento = (atletaId: number, professorId: number, opcoes: OpcoesCliente = {}): Promise<Resultado<null>> =>
  chamar<null>(`${atleta(atletaId)}/${encodeURIComponent(String(professorId))}/consentimento`, { method: "DELETE", headers: json }, opcoes, true);

/** Aguardando primeiro, depois consentidos, cada grupo por nome. Termo desatualizado conta como aguardando (o professor não vê). */
export function ordenar(vinculos: Vinculo[]): Vinculo[] {
  return [...vinculos].sort((a, b) => Number(a.consentimento) - Number(b.consentimento) || a.nome.localeCompare(b.nome, "pt-BR"));
}

export const totalAguardando = (vinculos: Vinculo[]) => vinculos.filter((v) => !v.consentimento).length;

/** "dd/mm/aa" da data ISO (no fuso do aparelho). */
export function dataCurta(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${String(d.getFullYear()).slice(-2)}`;
}
