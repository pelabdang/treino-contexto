import { router } from "expo-router";

import { TelaEvolucao } from "../../../componentes/TelaEvolucao";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta } from "../../../sessao/SessaoProvider";

// Evolução: os tiros de 1 km (cresce com o app: carga e forma, o normal).
export default function Evolucao() {
  const atualizar = useContadorDeFoco();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  return (
    <TelaEvolucao
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      atualizar={atualizar}
      ocultarEnviarFit
      aoAbrirTreino={(id) => router.push(`/treino/${id}`)}
    />
  );
}
