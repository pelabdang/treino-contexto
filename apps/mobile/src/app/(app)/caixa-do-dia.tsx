import { router } from "expo-router";
import { View } from "react-native";

import { BarraConta } from "../../componentes/BarraConta";
import { TelaCaixaDoDia } from "../../componentes/TelaCaixaDoDia";
import { useProfessor, useSessao } from "../../sessao/SessaoProvider";

export default function CaixaDoDia() {
  const { apiUrl, professorId, fetchFn } = useProfessor();
  const { sair } = useSessao();
  return (
    <View style={{ flex: 1 }}>
      <BarraConta aoTrocarSenha={() => router.push("/trocar-senha")} aoSair={sair} />
      <TelaCaixaDoDia apiUrl={apiUrl} professorId={professorId} fetchFn={fetchFn} />
    </View>
  );
}
