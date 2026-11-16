// Folha "Tipo do treino" (#427, spec docs/design/telas/caixa-do-dia.md). Abre com "Mudar tipo"; escolher fecha na hora.
// Celular: folha de baixo; computador: caixa centrada de 400. Fecha com "Fechar", Esc (onRequestClose) e toque fora.
import { MaterialIcons } from "@expo/vector-icons";
import { type ComponentRef, useEffect, useMemo, useRef } from "react";
import { Modal, Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import { TIPOS, type TipoTreino } from "../caixa/api";
import { FOCAVEL, focar } from "../navegacao/foco";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Props = {
  visivel: boolean;
  /** "Atleta Fixture Ana · Corrida de terça 11/11" (nome e data; nada de saúde). */
  subtitulo: string;
  sugerido: TipoTreino;
  /** Tipo hoje valendo na linha: o corrigido ou o sugerido. */
  escolhido: TipoTreino;
  aoEscolher: (tipo: TipoTreino) => void;
  aoFechar: () => void;
};

export function FolhaTipo({ visivel, subtitulo, sugerido, escolhido, aoEscolher, aoFechar }: Props) {
  const tema = useTema();
  const titulo = useRef<ComponentRef<typeof Text>>(null);
  // Ao abrir, o foco vai ao título (o `Modal` do react-native-web já prende o Tab dentro dele).
  useEffect(() => {
    if (!visivel) return;
    const t = setTimeout(() => focar(titulo.current), 0);
    return () => clearTimeout(t);
  }, [visivel]);
  const computador = useWindowDimensions().width >= 900;
  const styles = useMemo(() => criarEstilos(tema, computador), [tema, computador]);
  return (
    <Modal visible={visivel} transparent animationType="none" onRequestClose={aoFechar} accessibilityViewIsModal>
      <Pressable testID="fundo-folha" accessibilityLabel="Fechar" onPress={aoFechar} style={styles.fundo}>
        <Pressable role="dialog" aria-modal aria-label="Tipo do treino" accessible={false} onPress={() => {}} style={styles.folha}>
          <View style={styles.topo}>
            <Text ref={titulo} {...FOCAVEL} accessibilityRole="header" style={styles.titulo}>
              Tipo do treino
            </Text>
            <Pressable accessibilityRole="button" accessibilityLabel="Fechar" onPress={aoFechar} style={comFoco(styles.fechar, styles.foco)}>
              <MaterialIcons name="close" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
            </Pressable>
          </View>
          <Text style={styles.subtitulo}>{subtitulo}</Text>
          <View role="radiogroup" aria-label="Tipo do treino">
            {TIPOS.map((t) => {
              const marcado = t.valor === escolhido;
              return (
                <Pressable
                  key={t.valor}
                  testID={`tipo-${t.valor}`}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: marcado, selected: marcado }}
                  accessibilityLabel={t.valor === sugerido ? `${t.texto}, sugerido` : t.texto}
                  onPress={() => aoEscolher(t.valor)}
                  style={comFoco([styles.opcao, marcado && styles.opcaoMarcada], styles.foco)}
                >
                  <MaterialIcons name={marcado ? "radio-button-checked" : "radio-button-unchecked"} size={tamanho.iconeGrande} color={marcado ? tema.cor.destaque : tema.cor["borda-forte"]} accessible={false} />
                  <Text style={styles.opcaoTexto}>{t.texto}</Text>
                  {t.valor === sugerido && <Text style={styles.sugerido}>Sugerido</Text>}
                  {marcado && <MaterialIcons name="check" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />}
                </Pressable>
              );
            })}
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function criarEstilos({ cor }: Tema, computador: boolean) {
  return StyleSheet.create({
    fundo: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: computador ? "center" : "flex-end", alignItems: "center" },
    folha: {
      width: "100%",
      maxWidth: 400,
      padding: espaco[4],
      gap: espaco[2],
      backgroundColor: cor.superficie,
      borderTopLeftRadius: raio.grande,
      borderTopRightRadius: raio.grande,
      ...(computador ? { borderBottomLeftRadius: raio.grande, borderBottomRightRadius: raio.grande } : {}),
      borderWidth: borda.fina,
      borderColor: cor.borda,
    },
    topo: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
    titulo: { ...fonte["titulo-secao"], color: cor.texto },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
    fechar: { width: tamanho.alvoMinimo, height: tamanho.alvoMinimo, alignItems: "center", justifyContent: "center" },
    subtitulo: { ...fonte.rotulo, color: cor["texto-2"] },
    opcao: { minHeight: 56, flexDirection: "row", alignItems: "center", gap: espaco[3], paddingHorizontal: espaco[3], borderRadius: raio.medio, borderWidth: 2, borderColor: "transparent" },
    opcaoMarcada: { backgroundColor: cor["destaque-suave"], borderColor: cor.destaque },
    opcaoTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    sugerido: { ...fonte.legenda, color: cor["texto-2"] },
  });
}
