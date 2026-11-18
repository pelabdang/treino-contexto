import { router, useLocalSearchParams } from "expo-router";

import { TelaTermo } from "../../../componentes/TelaTermo";
import { useAtleta } from "../../../sessao/SessaoProvider";

export default function Termo() {
  const { professorId } = useLocalSearchParams<{ professorId: string }>();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  const voltar = () => (router.canGoBack() ? router.back() : router.replace("/consentimento"));
  return (
    <TelaTermo
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      professorId={Number(Array.isArray(professorId) ? professorId[0] : professorId)}
      aoVoltar={voltar}
      aoConcluir={() => (router.canGoBack() ? router.dismissTo("/consentimento?aviso=registrado") : router.replace("/consentimento?aviso=registrado"))}
      aoInexistente={() => router.replace("/consentimento?aviso=inexistente")}
    />
  );
}
