import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  useFonts,
} from "@expo-google-fonts/inter";

/** Carrega a Inter. Se falhar, o app segue com a fonte do sistema. */
export function useFontesInter(): boolean {
  const [carregadas, erro] = useFonts({ Inter_400Regular, Inter_500Medium, Inter_600SemiBold, Inter_700Bold });
  return carregadas || erro !== null;
}
