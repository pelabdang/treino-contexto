// Ícone falso para os testes: o MaterialIcons real tenta carregar a fonte (asset) e quebra no Jest.
import { Text } from "react-native";

export const MaterialIcons = ({ name }: { name: string }) => <Text accessibilityElementsHidden>{`[${name}]`}</Text>;
