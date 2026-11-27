import type { SerieCatalogo } from "@treino/api-client";
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo, useState } from "react";
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

export const NOME_MODALIDADE: Record<SerieCatalogo["modalidade"], string> = {
  corrida: "Corrida",
  natacao: "Natação",
  ciclismo: "Ciclismo",
  geral: "Geral",
};
const ORDEM: SerieCatalogo["modalidade"][] = ["corrida", "natacao", "ciclismo", "geral"];

type Props = {
  series: SerieCatalogo[];
  /** Id da série escolhida. */
  escolhida: string;
  aoEscolher: (serie: SerieCatalogo) => void;
  /** Computador (≥ 900): grupos numa coluna fixa, sem folha. */
  larga: boolean;
  /** Muda para abrir a folha de fora (o link "Escolher outra série"). */
  abrirFolha?: number;
};

/** Seletor em 2 passos: modalidade (segmento) e série (agrupada). Indisponível aparece cinza com o motivo escrito. */
export function SeletorSerie({ series, escolhida, aoEscolher, larga, abrirFolha = 0 }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const atual = series.find((s) => s.id === escolhida) ?? series[0];
  const modalidades = ORDEM.filter((m) => series.some((s) => s.modalidade === m));
  const [modalidade, setModalidade] = useState(atual?.modalidade ?? modalidades[0]);
  const [aberta, setAberta] = useState(false);
  const [vistoAbrir, setVistoAbrir] = useState(abrirFolha);
  if (abrirFolha !== vistoAbrir) {
    setVistoAbrir(abrirFolha);
    if (abrirFolha > 0) setAberta(true);
  }
  // Se a série escolhida de fora (início, memória) é de outra modalidade, o segmento a acompanha.
  const [vistoAtual, setVistoAtual] = useState(atual?.id);
  if (atual && atual.id !== vistoAtual) {
    setVistoAtual(atual.id);
    setModalidade(atual.modalidade);
  }
  if (!atual) return null;

  const daModalidade = series.filter((s) => s.modalidade === modalidade);
  const grupos = daModalidade.reduce<{ nome: string; itens: SerieCatalogo[] }[]>((acc, s) => {
    const g = acc.find((x) => x.nome === s.grupo);
    if (g) g.itens.push(s);
    else acc.push({ nome: s.grupo, itens: [s] });
    return acc;
  }, []);

  const trocarModalidade = (m: SerieCatalogo["modalidade"]) => {
    setModalidade(m);
    // Trocar de modalidade vai para a primeira série disponível dela (a primeira, se nenhuma estiver disponível).
    const dela = series.filter((s) => s.modalidade === m);
    aoEscolher(dela.find((s) => s.disponivel) ?? dela[0]);
  };

  const linha = (s: SerieCatalogo) => {
    const marcada = s.id === escolhida;
    const rotulo = `${s.titulo}. ${s.disponivel ? s.descricao : s.motivo ?? "Indisponível"}${marcada ? ". Selecionada" : ""}${s.disponivel ? "" : ". Indisponível"}`;
    return (
      <Pressable
        key={s.id}
        testID={`serie-${s.id}`}
        accessibilityRole="button"
        accessibilityState={{ selected: marcada }}
        accessibilityLabel={rotulo}
        onPress={() => {
          setAberta(false);
          aoEscolher(s);
        }}
        style={[styles.linha, marcada && styles.linhaMarcada, larga && marcada && styles.linhaLargaMarcada]}
      >
        <View style={styles.linhaTextos}>
          <Text style={[styles.linhaTitulo, !s.disponivel && styles.cinza]}>{s.titulo}</Text>
          <Text style={[styles.linhaDescricao, !s.disponivel && styles.cinza]}>{s.disponivel ? s.descricao : s.motivo}</Text>
        </View>
        {marcada && <MaterialIcons name="check" size={tamanho.iconeMedio} color={tema.cor.link} accessible={false} />}
      </Pressable>
    );
  };

  const lista = grupos.map((g) => (
    <View key={g.nome} accessibilityRole="list">
      <Text accessibilityRole="header" style={styles.grupo}>
        {g.nome}
      </Text>
      {g.itens.map(linha)}
    </View>
  ));

  return (
    <View testID="seletor-serie">
      {modalidades.length > 1 && (
        <View accessibilityRole="tablist" style={styles.segmento}>
          {modalidades.map((m) => {
            const ativa = m === modalidade;
            return (
              <Pressable
                key={m}
                testID={`modalidade-${m}`}
                accessibilityRole="tab"
                accessibilityState={{ selected: ativa }}
                onPress={() => trocarModalidade(m)}
                style={[styles.segmentoItem, ativa && styles.segmentoAtivo]}
              >
                <Text style={[styles.segmentoTexto, ativa && styles.segmentoTextoAtivo]}>{NOME_MODALIDADE[m]}</Text>
              </Pressable>
            );
          })}
        </View>
      )}
      {larga ? (
        <View testID="coluna-series">{lista}</View>
      ) : (
        <>
          <Text style={styles.rotuloCampo}>SÉRIE</Text>
          <Pressable
            testID="abrir-seletor"
            accessibilityRole="button"
            accessibilityLabel={`Série: ${atual.titulo}. Toque para trocar`}
            onPress={() => setAberta(true)}
            style={styles.campo}
          >
            <View style={styles.linhaTextos}>
              <Text style={styles.linhaTitulo}>{atual.titulo}</Text>
              <Text style={styles.linhaDescricao}>{atual.descricao}</Text>
            </View>
            <MaterialIcons name="expand-more" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
          </Pressable>
          <Modal visible={aberta} transparent animationType="none" onRequestClose={() => setAberta(false)}>
            <View style={styles.fundoFolha}>
              <View testID="folha-series" accessibilityViewIsModal style={styles.folha}>
                <View style={styles.folhaTopo}>
                  <Text accessibilityRole="header" style={styles.folhaTitulo}>
                    {NOME_MODALIDADE[modalidade]}: o que acompanhar
                  </Text>
                  <Pressable testID="fechar-seletor" accessibilityRole="button" onPress={() => setAberta(false)} style={styles.fechar}>
                    <Text style={styles.fecharTexto}>Fechar</Text>
                  </Pressable>
                </View>
                <ScrollView>{lista}</ScrollView>
              </View>
            </View>
          </Modal>
        </>
      )}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    segmento: { flexDirection: "row", gap: espaco[2], flexWrap: "wrap", marginBottom: espaco[3] },
    segmentoItem: {
      minHeight: tamanho.alvoMinimo,
      justifyContent: "center",
      paddingHorizontal: espaco[4],
      borderRadius: raio.botao,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    segmentoAtivo: { backgroundColor: cor["marca-suave"], borderColor: cor.link },
    segmentoTexto: { ...fonte.rotulo, color: cor.texto },
    segmentoTextoAtivo: { color: cor.link, fontWeight: "700" },
    rotuloCampo: { ...fonte.sobretitulo, color: cor["texto-2"], marginBottom: espaco[1] },
    campo: {
      minHeight: 56,
      flexDirection: "row",
      alignItems: "center",
      gap: espaco[2],
      paddingHorizontal: espaco[3],
      borderRadius: raio.bloco,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    linha: { minHeight: 56, flexDirection: "row", alignItems: "center", gap: espaco[2], paddingHorizontal: espaco[3], paddingVertical: espaco[2] },
    linhaMarcada: { backgroundColor: cor["marca-suave"] },
    linhaLargaMarcada: { borderLeftWidth: 3, borderLeftColor: cor.link },
    linhaTextos: { flex: 1 },
    linhaTitulo: { ...fonte["titulo-cartao"], color: cor.texto },
    linhaDescricao: { ...fonte.rotulo, color: cor["texto-2"] },
    cinza: { color: cor["texto-desligado"] },
    grupo: { ...fonte.sobretitulo, color: cor["texto-2"], paddingHorizontal: espaco[3], paddingTop: espaco[3], paddingBottom: espaco[1] },
    fundoFolha: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(0,0,0,0.4)" },
    folha: { maxHeight: "80%", backgroundColor: cor.superficie, borderTopLeftRadius: raio.cartao, borderTopRightRadius: raio.cartao, paddingBottom: espaco[4] },
    folhaTopo: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: espaco[3] },
    folhaTitulo: { ...fonte["titulo-secao"], color: cor.texto, flex: 1 },
    fechar: { minHeight: tamanho.alvoMinimo, minWidth: tamanho.alvoMinimo, justifyContent: "center", alignItems: "center", paddingHorizontal: espaco[2] },
    fecharTexto: { ...fonte.botao, color: cor.link },
  });
}
