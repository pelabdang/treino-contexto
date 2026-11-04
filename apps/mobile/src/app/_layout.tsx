import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { useTema } from "../tema";
import { useFontesInter } from "../tema/fontes";

export default function RootLayout() {
  const prontas = useFontesInter();
  const { cor } = useTema();
  if (!prontas) return null;
  return (
    <>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: cor.fundo } }} />
    </>
  );
}
