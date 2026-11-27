// Barra fixa do lote (#427): diz o que vai acontecer antes de salvar; só existe com pelo menos um treino selecionado.
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

export type ErroLote = { texto: string; atualizar: boolean };

type Props = {
  selecionados: number;
  corrigidos: number;
  salvando: boolean;
  erro: ErroLote | null;
  aoLimpar: () => void;
  aoSalvar: () => void;
  /** "Atualizar" do erro: atualiza a lista e limpa a seleção. */
  aoAtualizar: () => void;
  /** Altura medida da barra (`onLayout`), para a lista reservar o espaço certo no fim. */
  aoMedir?: (altura: number) => void;
};

export const textoSelecionados = (n: number, c: number) => `${n} ${n === 1 ? "selecionado" : "selecionados"} · ${c} ${c === 1 ? "corrigido" : "corrigidos"}`;
export const textoSalvar = (n: number) => `Salvar ${n} ${n === 1 ? "tipo" : "tipos"}`;

export function BarraLote({ selecionados, corrigidos, salvando, erro, aoLimpar, aoSalvar, aoAtualizar, aoMedir }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  return (
    <View role="region" aria-label="Ações do lote" testID="barra-lote" style={styles.barra} onLayout={(e) => aoMedir?.(e.nativeEvent.layout.height)}>
      <View style={styles.miolo}>
        {erro && (
          <View testID="erro-lote" accessibilityRole="alert" style={styles.erro}>
            <MaterialIcons name="error-outline" size={tamanho.iconeMedio} color={tema.cor.erro} accessible={false} />
            <Text style={styles.erroTexto}>{erro.texto}</Text>
            {erro.atualizar && (
              <Pressable accessibilityRole="button" onPress={aoAtualizar} style={comFoco(styles.textoBotao, styles.foco)}>
                <Text style={styles.link}>Atualizar</Text>
              </Pressable>
            )}
          </View>
        )}
        {salvando ? (
          <View testID="salvando" style={styles.linha} accessibilityLiveRegion="polite">
            <ActivityIndicator color={tema.cor.link} />
            <Text style={styles.texto}>Salvando...</Text>
          </View>
        ) : (
          <View style={styles.linha}>
            <Text testID="resumo-lote" accessibilityLiveRegion="polite" style={styles.texto}>
              {textoSelecionados(selecionados, corrigidos)}
            </Text>
            <Pressable testID="limpar-lote" accessibilityRole="button" onPress={aoLimpar} style={comFoco(styles.secundario, styles.foco)}>
              <Text style={styles.secundarioTexto}>Limpar seleção</Text>
            </Pressable>
            <Pressable testID="salvar-lote" accessibilityRole="button" onPress={aoSalvar} style={comFoco(styles.primario, styles.foco)}>
              <Text style={styles.primarioTexto}>{textoSalvar(selecionados)}</Text>
            </Pressable>
          </View>
        )}
        <Text style={styles.legenda}>Depois de salvar, para mudar de novo é só corrigir o tipo outra vez.</Text>
      </View>
    </View>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    barra: { position: "absolute", left: 0, right: 0, bottom: 0, backgroundColor: cor.superficie, borderTopWidth: borda.fina, borderTopColor: cor.borda },
    miolo: { width: "100%", maxWidth: larguraConteudoMax + 2 * margem, alignSelf: "center", padding: margem, gap: espaco[2] },
    linha: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: espaco[3] },
    texto: { ...fonte["corpo-forte"], color: cor.texto, flexGrow: 1 },
    legenda: { ...fonte.legenda, color: cor["texto-2"] },
    secundario: { minHeight: tamanho.botaoAltura, justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.botao, borderWidth: borda.fina, borderColor: cor["borda-forte"] },
    secundarioTexto: { ...fonte.botao, color: cor.texto },
    primario: { minHeight: tamanho.botaoAltura, justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.botao, backgroundColor: cor.botao },
    primarioTexto: { ...fonte.botao, color: cor["sobre-botao"] },
    erro: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: espaco[2], padding: espaco[3], borderRadius: raio.bloco, backgroundColor: cor["erro-suave"] },
    erroTexto: { ...fonte.corpo, color: cor.erro, flex: 1, minWidth: 200 },
    textoBotao: { minHeight: tamanho.alvoMinimo, justifyContent: "center" },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
    link: { ...fonte.botao, color: cor.link },
  });
}
