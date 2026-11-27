// Cartão "Comparado com o seu normal" (#465, spec #463, `linha_base@3`, ADR 0011). Só textos e números prontos da API.
// É comparação com o histórico do próprio atleta, nunca julgamento: `fora` não usa `cor.alerta` nem `cor.erro`.
import { MaterialIcons } from "@expo/vector-icons";
import type { Atividade, EstadoMetricaLinhaBase } from "@treino/api-client";
import { useMemo } from "react";
import { StyleSheet, Text, View } from "react-native";

import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Icone = "adjust" | "unfold-more" | "hourglass-empty" | "info-outline";

// A palavra de cada estado é fixa no app (spec #463); o ícone nunca é a única informação.
const ESTADOS: Record<EstadoMetricaLinhaBase, { icone: Icone; palavra: string }> = {
  dentro: { icone: "adjust", palavra: "Dentro do seu normal" },
  fora: { icone: "unfold-more", palavra: "Fora do seu normal" },
  aprendendo: { icone: "hourglass-empty", palavra: "Aprendendo o seu normal" },
  sem_valor: { icone: "info-outline", palavra: "Sem dado neste treino" },
};

export const NOTA_NORMAL = "Compara com o seu histórico no mesmo tipo de treino. Não diz se o treino foi bom ou ruim.";

export function CartaoNormal({ linhaBase }: { linhaBase: Atividade["linha_base"] }) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  if (!linhaBase) return null;
  // Treino inteiro ou troca (multiesporte): o texto não ajuda o atleta, o cartão não aparece.
  if (linhaBase.estado === "sem_linha_base" && linhaBase.motivo === "multiesporte") return null;

  return (
    <View testID="cartao-normal" style={styles.cartao}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Comparado com o seu normal
      </Text>
      {linhaBase.estado === "ok" ? (
        <>
          {linhaBase.metricas.map((m, i) => {
            const e = ESTADOS[m.estado];
            const fora = m.estado === "fora";
            const suave = m.estado !== "fora";
            return (
              <View
                key={m.chave}
                testID={`metrica-${m.chave}`}
                accessible
                accessibilityLabel={[m.rotulo, m.valor_texto, e.palavra, m.texto].filter(Boolean).join(". ")}
                style={[styles.metrica, i > 0 && styles.separador]}
              >
                <Text style={styles.rotulo}>{m.rotulo}</Text>
                <View style={styles.linhaValor}>
                  {m.valor_texto ? <Text style={styles.valor}>{m.valor_texto}</Text> : null}
                  <View style={[styles.estado, fora && styles.estadoFora]}>
                    <MaterialIcons name={e.icone} size={tamanho.iconePequeno} color={suave ? tema.cor["texto-2"] : tema.cor.texto} />
                    <Text style={[styles.palavra, { color: suave ? tema.cor["texto-2"] : tema.cor.texto }]}>{e.palavra}</Text>
                  </View>
                </View>
                <Text style={styles.texto}>{m.texto}</Text>
              </View>
            );
          })}
          <Text style={styles.legenda}>{NOTA_NORMAL}</Text>
        </>
      ) : linhaBase.texto ? (
        <View testID="aviso-normal" style={styles.aviso}>
          <MaterialIcons name="info-outline" size={tamanho.iconePequeno} color={tema.cor.texto} />
          <Text style={styles.avisoTexto}>{linhaBase.texto}</Text>
        </View>
      ) : null}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { marginTop: espaco[4], padding: espaco[4], borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    titulo: { ...fonte["titulo-secao"], color: cor.texto, marginBottom: espaco[2] },
    metrica: { paddingVertical: espaco[2], gap: espaco[1] },
    separador: { borderTopWidth: borda.fina, borderTopColor: cor.borda },
    rotulo: { ...fonte.rotulo, color: cor["texto-2"] },
    linhaValor: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", columnGap: espaco[3], rowGap: espaco[1] },
    valor: { ...fonte["corpo-forte"], fontVariant: ["tabular-nums"], color: cor.texto },
    estado: { flexDirection: "row", alignItems: "center", gap: espaco[1] },
    estadoFora: { paddingHorizontal: espaco[2], paddingVertical: 2, borderRadius: raio.pilula, backgroundColor: cor["superficie-2"] },
    palavra: { ...fonte.rotulo },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    legenda: { ...fonte.legenda, marginTop: espaco[3], color: cor["texto-2"] },
    aviso: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2], padding: espaco[3], borderRadius: raio.bloco, backgroundColor: cor["superficie-2"] },
    avisoTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
  });
}
