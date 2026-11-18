import { router } from "expo-router";
import { View } from "react-native";

import { BarraConta } from "../../componentes/BarraConta";
import { TelaEvolucao } from "../../componentes/TelaEvolucao";
import { useContadorDeFoco } from "../../navegacao/useContadorDeFoco";
import { useAtleta, useSessao } from "../../sessao/SessaoProvider";

export default function Inicio() {
  const atualizar = useContadorDeFoco();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  const { sair } = useSessao();
  return (
    <View style={{ flex: 1 }}>
      <BarraConta aoTrocarSenha={() => router.push("/trocar-senha")} aoSair={sair} />
      <TelaEvolucao
        apiUrl={apiUrl}
        atletaId={atletaId}
        fetchFn={fetchFn}
        atualizar={atualizar}
        aoAbrirTreino={(id) => router.push(`/treino/${id}`)}
        aoAbrirSemanaPadrao={() => router.push("/semana-padrao")}
        aoAbrirCheckinsPendentes={() => router.push("/checkins-pendentes")}
      />
    </View>
  );
}
