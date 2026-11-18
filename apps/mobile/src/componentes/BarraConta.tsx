// Menu "Conta" do cabeçalho das telas principais (#502, spec docs/design/telas/entrar.md): "Trocar senha", "Consentimento" (só o atleta) e "Sair". Sair abre um diálogo
// em que "Cancelar" é o botão principal (sair por engano custa digitar a senha de novo).
import { MaterialIcons } from "@expo/vector-icons";
import { type ComponentRef, useEffect, useMemo, useRef, useState } from "react";
import { Modal, Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import { FOCAVEL, focar } from "../navegacao/foco";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, larguraConteudoMax, larguraMargemGrande, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  aoTrocarSenha: () => void;
  /** Só o atleta tem "Consentimento" (quem consente é ele, #503). Sem a função, o item não aparece. */
  aoConsentimento?: () => void;
  /** Depois de confirmar o diálogo. */
  aoSair: () => void;
};

export function BarraConta({ aoTrocarSenha, aoConsentimento, aoSair }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
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
        {aberto && (
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
            {aoConsentimento && (
              <Pressable
                testID="consentimento"
                accessibilityRole="button"
                onPress={() => {
                  setAberto(false);
                  aoConsentimento();
                }}
                style={comFoco(styles.item, styles.foco)}
              >
                <MaterialIcons name="verified-user" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
                <Text style={styles.itemTexto}>Consentimento</Text>
              </Pressable>
            )}
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
        )}
      </View>
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

function DialogoSair({ visivel, aoCancelar, aoConfirmar }: { visivel: boolean; aoCancelar: () => void; aoConfirmar: () => void }) {
  const tema = useTema();
  const computador = useWindowDimensions().width >= larguraMargemGrande;
  const styles = useMemo(() => criarEstilosDialogo(tema, computador), [tema, computador]);
  const titulo = useRef<ComponentRef<typeof Text>>(null);
  useEffect(() => {
    if (!visivel) return;
    const t = setTimeout(() => focar(titulo.current), 0);
    return () => clearTimeout(t);
  }, [visivel]);
  return (
    <Modal visible={visivel} transparent animationType="none" onRequestClose={aoCancelar} accessibilityViewIsModal>
      <View style={styles.fundo}>
        <View role="dialog" aria-modal aria-label="Sair do app?" testID="dialogo-sair" style={styles.caixa}>
          <Text ref={titulo} {...FOCAVEL} accessibilityRole="header" style={styles.titulo}>
            Sair do app?
          </Text>
          <Text style={styles.texto}>Você vai precisar entrar de novo com o e-mail e a senha.</Text>
          <View style={styles.botoes}>
            <Pressable testID="cancelar-sair" accessibilityRole="button" onPress={aoCancelar} style={comFoco([styles.botao, styles.primario], styles.foco)}>
              <Text style={styles.primarioTexto}>Cancelar</Text>
            </Pressable>
            <Pressable testID="confirmar-sair" accessibilityRole="button" onPress={aoConfirmar} style={comFoco([styles.botao, styles.secundario], styles.foco)}>
              <Text style={styles.secundarioTexto}>Sair</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    barra: { alignItems: "center", paddingHorizontal: margem, paddingTop: espaco[2], zIndex: 1 },
    coluna: { width: "100%", maxWidth: larguraConteudoMax, alignItems: "flex-end" },
    botaoConta: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", gap: espaco[1], paddingHorizontal: espaco[2] },
    botaoContaTexto: { ...fonte.botao, color: cor.destaque },
    menu: { minWidth: 200, backgroundColor: cor.superficie, borderWidth: borda.fina, borderColor: cor.borda, borderRadius: raio.medio, padding: espaco[1] },
    item: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", gap: espaco[2], paddingHorizontal: espaco[3] },
    itemTexto: { ...fonte.corpo, color: cor.texto },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}

function criarEstilosDialogo({ cor }: Tema, computador: boolean) {
  return StyleSheet.create({
    fundo: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: computador ? "center" : "flex-end", alignItems: "center" },
    caixa: {
      width: "100%",
      maxWidth: 400,
      padding: espaco[4],
      gap: espaco[3],
      backgroundColor: cor.superficie,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      borderTopLeftRadius: raio.grande,
      borderTopRightRadius: raio.grande,
      ...(computador ? { borderBottomLeftRadius: raio.grande, borderBottomRightRadius: raio.grande } : {}),
    },
    titulo: { ...fonte["titulo-secao"], color: cor.texto },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    botoes: { flexDirection: "row", gap: espaco[3] },
    botao: { flex: 1, minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", borderRadius: raio.medio },
    primario: { backgroundColor: cor.destaque },
    primarioTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    secundario: { borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    secundarioTexto: { ...fonte.botao, color: cor.texto },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
