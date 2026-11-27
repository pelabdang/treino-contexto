// Símbolo do Pulso (nome de trabalho): linha de pulso em quadrado volt. Mesmo desenho de docs/design/marca/logo-pulso-simbolo.svg.
// A marca é a mesma nos temas claro e escuro, mas no escuro o volt é o `cor.marca` do tema (#D2FF3C).
import Svg, { Polyline, Rect } from "react-native-svg";

import { useTema } from "../tema";

type Props = { tamanho?: number };

/** Decorativo: o nome do app vem escrito ao lado (leitor de tela ignora o desenho). */
export function LogoPulso({ tamanho = 40 }: Props) {
  const { cor } = useTema();
  return (
    <Svg testID="logo-pulso" width={tamanho} height={tamanho} viewBox="0 0 128 128" accessible={false} importantForAccessibility="no-hide-descendants">
      <Rect width={128} height={128} rx={28} fill={cor.marca} />
      <Polyline
        fill="none"
        stroke={cor["sobre-marca"]}
        strokeWidth={11}
        strokeLinecap="round"
        strokeLinejoin="round"
        points="19.2,70.4 44.8,70.4 57.6,28.8 76.8,102.4 89.6,70.4 108.8,70.4"
      />
    </Svg>
  );
}
