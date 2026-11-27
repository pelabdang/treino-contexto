// Estado vazio provisório da aba "Treinos" (a lista de todos os treinos depende de uma rota da API que ainda não existe).
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import { espaco, fonte, larguraConteudoMax, tamanho, useMargemTela, useTema, type Tema } from "../tema";

export const TEXTO_EM_BREVE = "Em breve, todos os seus treinos aqui";

export function TelaEmBreve({ titulo }: { titulo: string }) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  return (
    <ScrollView testID="tela-em-breve" contentContainerStyle={styles.container}>
      <View style={styles.coluna}>
        <Text accessibilityRole="header" style={styles.titulo}>
          {titulo}
        </Text>
        <View style={styles.estado}>
          <MaterialIcons name="fitness-center" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
          <Text style={styles.texto}>{TEXTO_EM_BREVE}</Text>
        </View>
      </View>
    </ScrollView>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    container: { padding: margem, alignItems: "center" },
    coluna: { width: "100%", maxWidth: larguraConteudoMax, gap: espaco[3] },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    estado: { alignItems: "center", gap: espaco[3], paddingVertical: espaco[6] },
    texto: { ...fonte.corpo, color: cor["texto-2"], textAlign: "center" },
  });
}
