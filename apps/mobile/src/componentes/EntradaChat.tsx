// Ponto de entrada simples do chat no Início atual (#600). O Início v5 (#601) ainda não foi aprovado e vai redesenhar este bloco; por isso
// ele é um componente só, ligado por uma prop (`aoAbrirChat`) e por `ENTRADA_CHAT_NO_INICIO` em src/chat/textos.ts.
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { CHAMADA_ENTRADA, TITULO_CHAT } from "../chat/textos";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

export function EntradaChat({ aoAbrir }: { aoAbrir: () => void }) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  return (
    <Pressable testID="entrada-chat" accessibilityRole="button" accessibilityLabel={`${TITULO_CHAT}. ${CHAMADA_ENTRADA}`} onPress={aoAbrir} style={comFoco(styles.cartao, styles.foco)}>
      <MaterialIcons name="chat-bubble-outline" size={tamanho.iconeGrande} color={tema.cor.link} accessible={false} />
      <View style={styles.textos}>
        <Text style={styles.titulo}>{TITULO_CHAT}</Text>
        <Text style={styles.chamada}>{CHAMADA_ENTRADA}</Text>
      </View>
      <MaterialIcons name="chevron-right" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
    </Pressable>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { minHeight: tamanho.listaLinhaAltura, flexDirection: "row", alignItems: "center", gap: espaco[3], padding: espaco[3], borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    textos: { flex: 1 },
    titulo: { ...fonte["titulo-cartao"], color: cor.texto },
    chamada: { ...fonte.rotulo, color: cor["texto-2"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
