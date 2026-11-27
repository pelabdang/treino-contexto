// Dados do início v3. A quinzena é `GET /atletas/{id}/carga?ultimos=14` (o cliente do pacote só recorta por datas). Nunca lança.
import type { OpcoesCliente, Resultado, SerieCarga } from "@treino/api-client";

import { chamar } from "../checkin/api";

export function buscarQuinzena(atletaId: number, opcoes: OpcoesCliente = {}): Promise<Resultado<SerieCarga>> {
  return chamar<SerieCarga>(`/atletas/${encodeURIComponent(String(atletaId))}/carga?ultimos=14`, { headers: { Accept: "application/json" } }, opcoes);
}
