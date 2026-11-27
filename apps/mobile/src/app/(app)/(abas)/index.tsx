import { router } from "expo-router";

import { TelaEvolucao } from "../../../componentes/TelaEvolucao";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta } from "../../../sessao/SessaoProvider";

// Início: por enquanto, a tela de evolução atual. A tela inicial nova vem da proposta da Lia.
export default function Inicio() {
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
      aoAbrirCheckinsPendentes={() => router.navigate("/treinos?filtro=sem-checkin")}
    />
  );
}
