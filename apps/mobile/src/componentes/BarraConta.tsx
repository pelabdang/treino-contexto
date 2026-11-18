// Menu "Conta" do cabeçalho das telas principais (#502, spec docs/design/telas/entrar.md): "Trocar senha" e "Sair". Sair abre um diálogo
// em que "Cancelar" é o botão principal (sair por engano custa digitar a senha de novo). "Consentimento" (atleta) entra com a #503.
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo, useState } from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { DialogoSair } from "./DialogoSair";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  aoTrocarSenha: () => void;
  /** Depois de confirmar o diálogo. */
  aoSair: () => void;
};

export function BarraConta({ aoTrocarSenha, aoSair }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const topo = useSafeAreaInsets().top;
  const [aberto, setAberto] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  return (
    <View style={styles.barra}>
      <View style={styles.coluna}>
        <Pressable
          testID="abrir-conta"
          accessibilityRole="button"
          accessibilityLabel="Conta"
          accessibilityState={{ expanded: aberto }}
          onPress={() => setAberto((v) => !v)}
          style={comFoco(styles.botaoConta, styles.foco)}
        >
          <MaterialIcons name="account-circle" size={tamanho.iconeGrande} color={tema.cor.destaque} accessible={false} />
          <Text style={styles.botaoContaTexto}>Conta</Text>
          <MaterialIcons name={aberto ? "expand-less" : "expand-more"} size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
        </Pressable>
      </View>
      {/* O menu fica num Modal transparente: tocar fora e a tecla Esc (onRequestClose) fecham. */}
      <Modal visible={aberto} transparent animationType="none" onRequestClose={() => setAberto(false)}>
        <Pressable testID="fundo-menu-conta" accessible={false} focusable={false} importantForAccessibility="no" aria-hidden style={StyleSheet.absoluteFill} onPress={() => setAberto(false)} />
        <View pointerEvents="box-none" style={[styles.sobre, { paddingTop: topo + espaco[2] + tamanho.botaoAltura }]}>
          <View style={styles.colunaMenu}>
          <View testID="menu-conta" style={styles.menu}>
            <Pressable
              testID="trocar-senha"
              accessibilityRole="button"
              onPress={() => {
                setAberto(false);
                aoTrocarSenha();
              }}
              style={comFoco(styles.item, styles.foco)}
            >
              <MaterialIcons name="lock-outline" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
              <Text style={styles.itemTexto}>Trocar senha</Text>
            </Pressable>
            <Pressable
              testID="sair"
              accessibilityRole="button"
              onPress={() => {
                setAberto(false);
                setConfirmando(true);
              }}
              style={comFoco(styles.item, styles.foco)}
            >
              <MaterialIcons name="logout" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
              <Text style={styles.itemTexto}>Sair</Text>
            </Pressable>
          </View>
          </View>
        </View>
      </Modal>
      <DialogoSair
        visivel={confirmando}
        aoCancelar={() => setConfirmando(false)}
        aoConfirmar={() => {
          setConfirmando(false);
          aoSair();
        }}
      />
    </View>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    barra: { alignItems: "center", paddingHorizontal: margem, paddingTop: espaco[2], zIndex: 1 },
    coluna: { width: "100%", maxWidth: larguraConteudoMax, alignItems: "flex-end" },
    botaoConta: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", gap: espaco[1], paddingHorizontal: espaco[2] },
    botaoContaTexto: { ...fonte.botao, color: cor.destaque },
    sobre: { flex: 1, alignItems: "center", paddingHorizontal: margem },
    colunaMenu: { width: "100%", maxWidth: larguraConteudoMax, alignItems: "flex-end" },
    menu: { minWidth: 200, backgroundColor: cor.superficie, borderWidth: borda.fina, borderColor: cor.borda, borderRadius: raio.medio, padding: espaco[1], width: 200 },
    item: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", gap: espaco[2], paddingHorizontal: espaco[3] },
    itemTexto: { ...fonte.corpo, color: cor.texto },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
