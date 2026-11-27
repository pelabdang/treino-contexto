import { router } from "expo-router";

import { TelaConta } from "../../../componentes/TelaConta";
import { usePedidos } from "../../../consentimento/usePedidos";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useSessao } from "../../../sessao/SessaoProvider";

export default function Conta() {
  const { estado, apiUrl, fetch: fetchFn, sair } = useSessao();
  const atualizar = useContadorDeFoco();
  const papel = estado.tipo === "dentro" ? estado.papel : "atleta";
  const atletaId = estado.tipo === "dentro" ? (estado.atletaId ?? 0) : 0;
  const pedidos = usePedidos(papel === "atleta" && atletaId > 0, apiUrl, atletaId, fetchFn, atualizar);
  return (
    <TelaConta
      papel={papel}
      nome={estado.tipo === "dentro" ? estado.nome : ""}
      pedidos={pedidos}
      aoAbrirSemanaPadrao={() => router.push("/semana-padrao")}
      aoAbrirConsentimento={() => router.push("/consentimento")}
      aoTrocarSenha={() => router.push("/trocar-senha")}
      aoSair={sair}
      envio={{ apiUrl, atletaId, fetchFn, aoEnviar: () => router.navigate("/") }}
    />
  );
}
