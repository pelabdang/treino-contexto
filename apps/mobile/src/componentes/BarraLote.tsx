// Barra fixa do lote (#427): diz o que vai acontecer antes de salvar; só existe com pelo menos um treino selecionado.
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

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
};

export const textoSelecionados = (n: number, c: number) => `${n} ${n === 1 ? "selecionado" : "selecionados"} · ${c} ${c === 1 ? "corrigido" : "corrigidos"}`;
export const textoSalvar = (n: number) => `Salvar ${n} ${n === 1 ? "tipo" : "tipos"}`;

export function BarraLote({ selecionados, corrigidos, salvando, erro, aoLimpar, aoSalvar, aoAtualizar }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  return (
    <View role="region" aria-label="Ações do lote" testID="barra-lote" style={styles.barra}>
      <View style={styles.miolo}>
        {erro && (
          <View testID="erro-lote" accessibilityRole="alert" style={styles.erro}>
            <MaterialIcons name="error-outline" size={tamanho.iconeMedio} color={tema.cor.erro} accessible={false} />
            <Text style={styles.erroTexto}>{erro.texto}</Text>
            {erro.atualizar && (
              <Pressable accessibilityRole="button" onPress={aoAtualizar} style={styles.textoBotao}>
                <Text style={styles.link}>Atualizar</Text>
              </Pressable>
            )}
          </View>
        )}
        {salvando ? (
          <View testID="salvando" style={styles.linha} accessibilityLiveRegion="polite">
            <ActivityIndicator color={tema.cor.destaque} />
            <Text style={styles.texto}>Salvando...</Text>
          </View>
        ) : (
          <View style={styles.linha}>
            <Text testID="resumo-lote" accessibilityLiveRegion="polite" style={styles.texto}>
              {textoSelecionados(selecionados, corrigidos)}
            </Text>
            <Pressable accessibilityRole="button" onPress={aoLimpar} style={styles.secundario}>
              <Text style={styles.secundarioTexto}>Limpar seleção</Text>
            </Pressable>
            <Pressable accessibilityRole="button" onPress={aoSalvar} style={styles.primario}>
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
    secundario: { minHeight: tamanho.botaoAltura, justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.medio, borderWidth: borda.fina, borderColor: cor["borda-forte"] },
    secundarioTexto: { ...fonte.botao, color: cor.texto },
    primario: { minHeight: tamanho.botaoAltura, justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.medio, backgroundColor: cor.destaque },
    primarioTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    erro: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: espaco[2], padding: espaco[3], borderRadius: raio.medio, backgroundColor: cor["erro-suave"] },
    erroTexto: { ...fonte.corpo, color: cor.erro, flex: 1, minWidth: 200 },
    textoBotao: { minHeight: tamanho.alvoMinimo, justifyContent: "center" },
    link: { ...fonte.botao, color: cor.destaque },
  });
}
