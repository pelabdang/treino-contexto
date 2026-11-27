// Abas do app (UX): base no celular, menu à esquerda no computador. As telas de detalhe (treino, check-in, semana-padrão,
// consentimento, trocar senha) abrem por cima, no Stack do grupo (app), sem a barra, e as URLs não mudam.
import { router, Tabs, usePathname } from "expo-router";
import { useWindowDimensions } from "react-native";

import { abasDoPapel, BarraDeAbas } from "../../../componentes/BarraDeAbas";
import { usePedidos } from "../../../consentimento/usePedidos";
import { useSessao } from "../../../sessao/SessaoProvider";
import { larguraMargemGrande, useTema } from "../../../tema";

export default function Abas() {
  const { cor } = useTema();
  const { estado, apiUrl, fetch: fetchFn } = useSessao();
  const computador = useWindowDimensions().width >= larguraMargemGrande;
  const papel = estado.tipo === "dentro" ? estado.papel : "atleta";
  const atletaId = estado.tipo === "dentro" ? (estado.atletaId ?? 0) : 0;
  const caminho = usePathname();
  // O selo da Conta se atualiza a cada troca de tela (por exemplo, depois de dar ou retirar o consentimento).
  const pedidos = usePedidos(papel === "atleta" && atletaId > 0, apiUrl, atletaId, fetchFn, caminho);
  const abas = abasDoPapel(papel);
  return (
    <Tabs
      screenOptions={{ headerShown: false, tabBarPosition: computador ? "left" : "bottom", sceneStyle: { backgroundColor: cor.fundo } }}
      tabBar={(props) => (
        <BarraDeAbas
          abas={abas}
          ativa={props.state.routes[props.state.index]?.name ?? ""}
          aoEscolher={(rota) => router.navigate((rota === "index" ? "/" : `/${rota}`) as "/")}
          lateral={computador}
          selos={{ conta: pedidos }}
        />
      )}
    >
      <Tabs.Screen name="index" options={{ href: papel === "atleta" ? undefined : null }} />
      <Tabs.Screen name="treinos" options={{ href: papel === "atleta" ? undefined : null }} />
      <Tabs.Screen name="evolucao" options={{ href: papel === "atleta" ? undefined : null }} />
      <Tabs.Screen name="caixa-do-dia" options={{ href: papel === "professor" ? undefined : null }} />
      <Tabs.Screen name="conta" />
    </Tabs>
  );
}
