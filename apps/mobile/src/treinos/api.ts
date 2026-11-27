// Lista de treinos do atleta (adendo 13 da ADR 0004): `GET /atletas/{id}/atividades`, mais recente primeiro, paginada por cursor.
// Tipos do cliente gerado. Nunca lança. Privacidade: nada do corpo vai para log, console nem mensagem de erro.
import type { components, OpcoesCliente, Resultado } from "@treino/api-client";

import { chamar } from "../checkin/api";

export type ListaTreinos = components["schemas"]["ListaOut"];
export type ItemTreino = components["schemas"]["ListaAtividadesItemOut"];
export type ModalidadeFiltro = "corrida" | "natacao" | "ciclismo";

export type FiltroTreinos = {
  modalidade?: ModalidadeFiltro | null;
  /** Só treinos que pedem check-in, ainda sem ele e dentro do prazo. */
  checkinPendente?: boolean;
  /** `proximo` da página anterior. */
  antesDe?: string | null;
  limite?: number;
};

export function buscarTreinos(atletaId: number, filtro: FiltroTreinos = {}, opcoes: OpcoesCliente = {}): Promise<Resultado<ListaTreinos>> {
  const q = new URLSearchParams();
  if (filtro.limite) q.set("limite", String(filtro.limite));
  if (filtro.antesDe) q.set("antes_de", filtro.antesDe);
  if (filtro.modalidade) q.set("modalidade", filtro.modalidade);
  if (filtro.checkinPendente) q.set("checkin_pendente", "true");
  const texto = q.toString();
  return chamar<ListaTreinos>(`/atletas/${encodeURIComponent(String(atletaId))}/atividades${texto ? `?${texto}` : ""}`, { headers: { Accept: "application/json" } }, opcoes);
}
