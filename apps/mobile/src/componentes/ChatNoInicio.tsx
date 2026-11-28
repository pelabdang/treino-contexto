// Bloco "Pergunte ao seu treino" do Início v5 (spec inicio-v5-direcoes, item 4): título com "Conversas ›", caixa, botão de enviar e a fileira
// de perguntas prontas (da API, com as 6 fixas de plano B; ver `usePerguntasProntas`). Toque numa pergunta abre o chat e já envia; toque na caixa abre o chat com o teclado.
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { EXEMPLO_DA_CAIXA, PERGUNTAS_PRONTAS_NO_INICIO, TITULO_CHAT } from "../chat/textos";
import { EsqueletoPerguntas } from "./Esqueleto";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Props = {
  /** Abre o chat com o teclado (caixa e botão de enviar). */
  aoAbrirChat: () => void;
  /** Abre o chat e envia a pergunta pronta de índice `indice` (de `PERGUNTAS_PRONTAS`). */
  aoPerguntar: (indice: number) => void;
  aoAbrirConversas: () => void;
  /** As perguntas prontas (da API ou o plano B), na mesma ordem do chat; `null` enquanto carrega (3 esqueletos). */
  perguntas: readonly string[] | null;
  /** Atleta sem treinos: sem perguntas prontas (spec do chat). */
  semProntas?: boolean;
};

export function ChatNoInicio({ aoAbrirChat, aoPerguntar, aoAbrirConversas, perguntas, semProntas = false }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  return (
    <View testID="chat-no-inicio" style={styles.bloco}>
      <View style={styles.titulos}>
        <Text accessibilityRole="header" style={styles.titulo}>
          {TITULO_CHAT}
        </Text>
        <Pressable testID="inicio-conversas" accessibilityRole="button" onPress={aoAbrirConversas} style={comFoco(styles.alvoLink, styles.foco)}>
          <Text style={styles.linkTexto}>Conversas ›</Text>
        </Pressable>
      </View>
      <View style={styles.linhaCaixa}>
        <Pressable testID="inicio-caixa" accessibilityRole="button" accessibilityLabel={TITULO_CHAT} onPress={aoAbrirChat} style={comFoco(styles.caixa, styles.foco)}>
          <Text style={styles.exemplo}>{EXEMPLO_DA_CAIXA}</Text>
        </Pressable>
        <Pressable testID="inicio-enviar" accessibilityRole="button" accessibilityLabel="Enviar pergunta" onPress={aoAbrirChat} style={comFoco(styles.enviar, styles.foco)}>
          <MaterialIcons name="arrow-upward" size={tamanho.iconeGrande} color={tema.cor["sobre-botao"]} accessible={false} />
        </Pressable>
      </View>
      {!semProntas && perguntas === null && (
        <View testID="inicio-prontas-carregando">
          <Text accessibilityLiveRegion="polite" style={styles.apenasLeitor}>Carregando perguntas sugeridas</Text>
          <EsqueletoPerguntas quantidade={3} linhas={false} />
        </View>
      )}
      {!semProntas && perguntas !== null && (
        <ScrollView testID="inicio-prontas" horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.prontas}>
          {perguntas.slice(0, PERGUNTAS_PRONTAS_NO_INICIO).map((q, i) => (
            <Pressable key={q} testID={`inicio-pronta-${i}`} accessibilityRole="button" onPress={() => aoPerguntar(i)} style={comFoco(styles.pronta, styles.foco)}>
              <Text style={styles.prontaTexto}>{q}</Text>
            </Pressable>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    bloco: { gap: espaco[3], padding: espaco[4], borderRadius: raio["cartao-destaque"], borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    titulos: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
    titulo: { ...fonte["titulo-secao"], color: cor.texto, flex: 1 },
    alvoLink: { minHeight: tamanho.alvoMinimo, justifyContent: "center" },
    linkTexto: { ...fonte.botao, color: cor.link },
    linhaCaixa: { flexDirection: "row", gap: espaco[2], alignItems: "center" },
    caixa: { flex: 1, minHeight: tamanho.botaoAltura, justifyContent: "center", paddingHorizontal: espaco[3], borderRadius: raio.botao, borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.fundo },
    exemplo: { ...fonte.corpo, color: cor["texto-2"] },
    enviar: { width: tamanho.botaoAltura, height: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", borderRadius: raio.botao, backgroundColor: cor.botao },
    apenasLeitor: { position: "absolute", width: 1, height: 1, opacity: 0 },
    prontas: { gap: espaco[2], paddingRight: espaco[4] },
    pronta: { minHeight: tamanho.alvoMinimo, justifyContent: "center", paddingHorizontal: espaco[3], borderRadius: raio.pilula, borderWidth: borda.fina, borderColor: cor["borda-forte"] },
    prontaTexto: { ...fonte.rotulo, color: cor.texto },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
