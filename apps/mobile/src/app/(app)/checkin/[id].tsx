import { router, useLocalSearchParams } from "expo-router";

import { TelaCheckin } from "../../../componentes/TelaCheckin";
import { useAtleta } from "../../../sessao/SessaoProvider";

// A rota leva só o id da atividade (e, da lista de pendentes, de onde a pessoa veio): nenhuma resposta passa por aqui.
export default function Checkin() {
  const { id, origem } = useLocalSearchParams<{ id: string; origem?: string }>();
  const atividadeId = Number(Array.isArray(id) ? id[0] : id);
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  const sair = () => (router.canGoBack() ? router.back() : router.replace(`/treino/${atividadeId}`));
  return (
    <TelaCheckin
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      atividadeId={atividadeId}
      origem={(Array.isArray(origem) ? origem[0] : origem) === "pendentes" ? "pendentes" : "treino"}
      aoVoltar={sair}
      aoConcluir={sair}
      aoApagado={sair}
    />
  );
}
