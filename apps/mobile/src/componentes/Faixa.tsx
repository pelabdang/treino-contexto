// Faixa de aviso da tela de entrada (spec docs/design/telas/entrar.md): erro (`error-outline`, cor.erro sobre cor.erro-suave) ou
// neutra (`info-outline`). Nunca depende só da cor: tem ícone e frase. O erro é lido como alerta quando aparece.
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo } from "react";
import { StyleSheet, Text, View } from "react-native";

import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Props = { tipo: "erro" | "info"; texto: string; testID?: string };

export function Faixa({ tipo, texto, testID }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const erro = tipo === "erro";
  return (
    <View
      testID={testID}
      accessible
      accessibilityRole={erro ? "alert" : undefined}
      accessibilityLiveRegion={erro ? "assertive" : "polite"}
      style={[styles.faixa, erro ? styles.erro : styles.info]}
    >
      <MaterialIcons name={erro ? "error-outline" : "info-outline"} size={tamanho.iconeGrande} color={erro ? tema.cor.erro : tema.cor["texto-2"]} accessible={false} />
      <Text style={[styles.texto, { color: erro ? tema.cor.erro : tema.cor.texto }]}>{texto}</Text>
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    faixa: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2], padding: espaco[3], borderRadius: raio.medio, borderWidth: borda.fina },
    erro: { backgroundColor: cor["erro-suave"], borderColor: cor.erro },
    info: { backgroundColor: cor["superficie-2"], borderColor: cor.borda },
    texto: { ...fonte.corpo, flex: 1 },
  });
}
