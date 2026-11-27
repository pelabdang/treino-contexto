import { BarlowCondensed_800ExtraBold } from "@expo-google-fonts/barlow-condensed";
import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Inter_800ExtraBold,
  useFonts,
} from "@expo-google-fonts/inter";

/** Carrega Inter e Barlow Condensed. Se falhar, o app segue com a fonte do sistema. */
export function useFontesInter(): boolean {
  const [carregadas, erro] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    Inter_800ExtraBold,
    BarlowCondensed_800ExtraBold,
  });
  return carregadas || erro !== null;
}
