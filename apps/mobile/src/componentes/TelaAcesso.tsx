// Telas de espera da abertura do app (#502, spec docs/design/telas/entrar.md, "Abrir o app"): verificando o acesso e sem rede.
// Sem rede NÃO manda para a entrada: a pessoa pode estar com acesso e só sem sinal.
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

export function TelaVerificando() {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  return (
    <View testID="verificando-acesso" style={styles.tela}>
      <Text accessibilityLiveRegion="polite" style={styles.texto}>
        Verificando o seu acesso...
      </Text>
    </View>
  );
}

export function TelaSemRede({ aoTentar }: { aoTentar: () => void }) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  return (
    <View testID="acesso-sem-rede" style={styles.tela}>
      <MaterialIcons name="wifi-off" size={tamanho.iconeEstado} color={tema.cor.erro} accessible={false} />
      <Text accessibilityRole="alert" style={styles.texto}>
        Não foi possível falar com o servidor
      </Text>
      <Pressable accessibilityRole="button" onPress={aoTentar} style={comFoco(styles.botao, styles.foco)}>
        <Text style={styles.botaoTexto}>Tentar de novo</Text>
      </Pressable>
    </View>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    tela: { flex: 1, alignItems: "center", justifyContent: "center", gap: espaco[3], padding: margem, backgroundColor: cor.fundo },
    texto: { ...fonte.corpo, color: cor.texto, textAlign: "center" },
    botao: { minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", borderRadius: raio.medio, backgroundColor: cor.destaque, paddingHorizontal: espaco[5] },
    botaoTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
