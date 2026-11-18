import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { View } from "react-native";

import { SessaoProvider } from "../sessao/SessaoProvider";
import { useTema } from "../tema";
import { useFontesInter } from "../tema/fontes";

export default function RootLayout() {
  const prontas = useFontesInter();
  const { cor } = useTema();
  // Enquanto a fonte carrega, mostra o fundo do tema (sem piscar em branco).
  if (!prontas) return <View testID="carregando-fonte" style={{ flex: 1, backgroundColor: cor.fundo }} />;
  return (
    <SessaoProvider>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: cor.fundo } }} />
    </SessaoProvider>
  );
}
