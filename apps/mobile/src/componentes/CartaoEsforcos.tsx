// Cartão "Esforços" (#467, spec #463): o que o atleta fez de forte, em texto e números prontos da API (ADR 0008). Sem cálculo no app.
import { MaterialIcons } from "@expo/vector-icons";
import type { Atividade, BlocoEsforco } from "@treino/api-client";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Esforcos = NonNullable<Atividade["esforcos"]>;

const MAXIMO = 8;
const SEM_DADO = "sem dado";

/** Número como a API mandou (vírgula decimal, sem arredondar). */
const numero = (n: number | null | undefined) => (n == null ? null : String(n).replace(".", ","));

export function CartaoEsforcos({ esforcos }: { esforcos: Esforcos | null | undefined }) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [todos, setTodos] = useState(false);
  if (!esforcos) return null;

  const blocos = esforcos.blocos;
  const relevantes = blocos.filter((b) => b.categoria !== "leve");
  if (relevantes.length === 0) return null; // só rodagem (ou vazio): o cartão não aparece

  const lista = blocos.filter((b) => b.categoria === "esforco").sort((a, b) => a.ordem - b.ordem);
  const aquecimento = blocos.filter((b) => b.categoria === "aquecimento");
  const desaquecimento = blocos.filter((b) => b.categoria === "desaquecimento");
  // Quem decide a segunda coluna é a presença do campo na resposta, não a modalidade.
  const temPace = lista.some((b) => b.pace != null);
  const temVelocidade = !temPace && lista.some((b) => b.velocidade != null);
  const visiveis = todos ? lista : lista.slice(0, MAXIMO);

  const primeira = (b: BlocoEsforco, i: number) => `${i + 1} · ${b.faixa_rotulo ?? b.distancia ?? b.duracao}`;
  const celula = (valor: string | null | undefined) =>
    valor ? <Text style={styles.valor}>{valor}</Text> : <Text style={styles.semDado}>{SEM_DADO}</Text>;

  return (
    <View testID="cartao-esforcos" style={styles.cartao}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Esforços
      </Text>

      {lista.length === 0 ? (
        <View testID="aviso-sem-esforco" style={styles.aviso}>
          <MaterialIcons name="info-outline" size={tamanho.iconePequeno} color={tema.cor.texto} />
          <Text style={styles.avisoTexto}>Nenhum esforço detectado neste treino.</Text>
        </View>
      ) : (
        <>
          {aquecimento.map((b) => (
            <Text key={`a${b.ordem}`} style={styles.rotulo}>
              Aquecimento {b.duracao}
            </Text>
          ))}
          <View style={styles.linha} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
            <Text style={[styles.rotulo, { flex: 2 }]}>Esforço</Text>
            {temPace && <Text style={[styles.rotulo, styles.col, styles.colTexto]}>Pace</Text>}
            {temVelocidade && <Text style={[styles.rotulo, styles.col, styles.colTexto]}>Velocidade</Text>}
            <Text style={[styles.rotulo, styles.col, styles.colTexto]}>FC</Text>
          </View>
          <View style={styles.linha} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
            <View style={{ flex: 2 }} />
            {temPace && <Text style={[styles.rotulo, styles.col, styles.colTexto]}>min/km</Text>}
            {temVelocidade && <Text style={[styles.rotulo, styles.col, styles.colTexto]}>km/h</Text>}
            <Text style={[styles.rotulo, styles.col, styles.colTexto]}>bpm</Text>
          </View>
          {visiveis.map((b, i) => {
            const segunda = temPace ? b.pace : temVelocidade ? b.velocidade : null;
            const fc = numero(b.fc_media);
            return (
              <View
                key={b.ordem}
                testID={`esforco-${i + 1}`}
                accessible
                accessibilityLabel={[
                  `Esforço ${primeira(b, i)}`,
                  temPace ? `pace ${segunda ?? SEM_DADO} por quilômetro` : temVelocidade ? `velocidade ${segunda ?? SEM_DADO} quilômetros por hora` : null,
                  `FC ${fc ?? SEM_DADO}`,
                  b.parada_apos ? `pausa ${b.parada_apos}` : null,
                ]
                  .filter(Boolean)
                  .join(", ")}
              >
                <View style={styles.linhaEsforco}>
                  <Text style={[styles.valor, { flex: 2, textAlign: "left" }]}>{primeira(b, i)}</Text>
                  {(temPace || temVelocidade) && <View style={styles.col}>{celula(segunda)}</View>}
                  <View style={styles.col}>{celula(fc)}</View>
                </View>
                {b.parada_apos ? <Text style={styles.legenda}>pausa {b.parada_apos}</Text> : null}
              </View>
            );
          })}
          {lista.length > MAXIMO && (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ expanded: todos }}
              onPress={() => setTodos((v) => !v)}
              style={styles.verTodos}
            >
              <Text style={styles.link}>{todos ? "Ver menos" : `Ver todos os ${lista.length} esforços`}</Text>
              <MaterialIcons name={todos ? "expand-less" : "expand-more"} size={tamanho.iconeMedio} color={tema.cor.destaque} />
            </Pressable>
          )}
          {desaquecimento.map((b) => (
            <Text key={`d${b.ordem}`} style={styles.rotulo}>
              Desaquecimento {b.duracao}
            </Text>
          ))}
        </>
      )}

      {esforcos.referencia_da_atividade && (
        <View testID="aviso-referencia" style={styles.aviso}>
          <MaterialIcons name="info-outline" size={tamanho.iconePequeno} color={tema.cor.texto} />
          <Text style={styles.avisoTexto}>Sem treinos anteriores parecidos: os esforços foram detectados só com este treino.</Text>
        </View>
      )}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { marginTop: espaco[4], padding: espaco[4], borderRadius: raio.grande, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    titulo: { ...fonte["titulo-secao"], color: cor.texto, marginBottom: espaco[2] },
    rotulo: { ...fonte.rotulo, color: cor["texto-2"], paddingVertical: espaco[1] },
    linha: { flexDirection: "row", alignItems: "center" },
    linhaEsforco: { flexDirection: "row", alignItems: "center", minHeight: tamanho.alvoMinimo },
    col: { flex: 1, alignItems: "flex-end" },
    colTexto: { textAlign: "right" },
    valor: { ...fonte["corpo-forte"], fontVariant: ["tabular-nums"], color: cor.texto, textAlign: "right" },
    semDado: { ...fonte.corpo, color: cor["texto-2"], textAlign: "right" },
    legenda: { ...fonte.legenda, color: cor["texto-2"], paddingBottom: espaco[2] },
    verTodos: { flexDirection: "row", alignItems: "center", gap: espaco[1], minHeight: tamanho.botaoAltura, alignSelf: "flex-start" },
    link: { ...fonte.botao, color: cor.destaque },
    aviso: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2], marginTop: espaco[2], padding: espaco[3], borderRadius: raio.medio, backgroundColor: cor["superficie-2"] },
    avisoTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
  });
}
