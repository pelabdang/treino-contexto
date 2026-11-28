import { router, useLocalSearchParams } from "expo-router";

import { TelaEvolucao } from "../../../componentes/TelaEvolucao";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta } from "../../../sessao/SessaoProvider";

// Evolução v1: séries por modalidade (spec evolucao-v1).
export default function Evolucao() {
  const atualizar = useContadorDeFoco();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  // `?serie=<id>`: vem dos cartões do início, que abrem a Evolução já nessa série.
  const { serie } = useLocalSearchParams<{ serie?: string }>();
  return (
    <TelaEvolucao
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      atualizar={atualizar}
      serieInicial={typeof serie === "string" && serie ? serie : undefined}
      ocultarEnviarFit
      aoAbrirTreino={(id) => router.push(`/treino/${id}`)}
    />
  );
}
