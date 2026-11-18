import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { SessaoProvider } from "../sessao/SessaoProvider";
import { useTema } from "../tema";
import { useFontesInter } from "../tema/fontes";

// Área segura (entalhe, barra de início): todas as telas ficam dentro dela, no topo, embaixo e nas laterais. Na web os valores são 0.
function AreaSegura({ children }: { children: React.ReactNode }) {
  const { cor } = useTema();
  const i = useSafeAreaInsets();
  return (
    <View testID="area-segura" style={{ flex: 1, backgroundColor: cor.fundo, paddingTop: i.top, paddingBottom: i.bottom, paddingLeft: i.left, paddingRight: i.right }}>
      {children}
    </View>
  );
}

export default function RootLayout() {
  const prontas = useFontesInter();
  const { cor } = useTema();
  // Enquanto a fonte carrega, mostra o fundo do tema (sem piscar em branco).
  if (!prontas) return <View testID="carregando-fonte" style={{ flex: 1, backgroundColor: cor.fundo }} />;
  return (
    <SessaoProvider>
      <StatusBar style="auto" />
      <AreaSegura>
        <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: cor.fundo } }} />
      </AreaSegura>
    </SessaoProvider>
  );
}
