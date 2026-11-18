// Diálogo "Sair do app?" (spec docs/design/telas/entrar.md): "Cancelar" é o botão principal (sair por engano custa digitar a senha de novo).
import { type ComponentRef, useEffect, useMemo, useRef } from "react";
import { Modal, Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import { FOCAVEL, focar } from "../navegacao/foco";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, larguraMargemGrande, raio, tamanho, useTema, type Tema } from "../tema";

export function DialogoSair({ visivel, aoCancelar, aoConfirmar }: { visivel: boolean; aoCancelar: () => void; aoConfirmar: () => void }) {
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
