import { MaterialIcons } from "@expo/vector-icons";
import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { comFoco } from "../tema/foco";
import type { ItemTreino } from "../treinos/api";
import { dataCurta } from "./GraficoTiros";
import { MODALIDADES } from "./modalidades";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

export const TIPOS: Record<string, string> = { leve: "Leve", moderado: "Moderado", longo: "Longo", intervalado: "Intervalado", fartlek: "Fartlek" };

type Selo = { chave: string; icone: React.ComponentProps<typeof MaterialIcons>["name"]; texto: string; atencao: boolean };

/** Cartão de treino da lista e do início (spec v3, seção 3): valor principal e um selo só. */
export function CartaoTreino({ item, aoAbrir }: { item: ItemTreino; aoAbrir: () => void }) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const mod = MODALIDADES[item.modalidade];
  const nome = mod?.nome ?? "Treino";
  const quando = `${dataCurta(item.data_local)} às ${item.hora_local}`;
  const tipo = item.tipo_treino ? TIPOS[item.tipo_treino] : null;
  // Um selo só, o primeiro que valer (spec v3): sem check-in, check-in vencido. Os selos de "normal" dependem de campo
  // que a lista ainda não traz (linha de base); entram quando a API mandar.
  const selo: Selo | null =
    item.checkin_estado === "pendente"
      ? { chave: "pendente", icone: "schedule", texto: "Sem check-in", atencao: true }
      : item.checkin_estado === "vencido"
        ? { chave: "vencido", icone: "event-busy", texto: "Check-in vencido", atencao: false }
        : null;
  const principal = item.destaque ?? item.duracao;
  const resumo = [nome, quando, tipo, item.duracao, item.distancia, selo?.texto].filter(Boolean).join(", ");
  return (
    <Pressable
      testID={`treino-${item.atividade_id}`}
      accessibilityRole="button"
      accessibilityLabel={resumo}
      onPress={aoAbrir}
      style={comFoco(styles.cartao, styles.foco)}
    >
      <View style={styles.topo}>
        {mod && <MaterialIcons name={mod.icone} size={tamanho.iconeGrande} color={tema.cor[mod.cor]} accessible={false} />}
        <Text style={styles.nome}>{nome}</Text>
        {tipo && (
          <View style={styles.tipo}>
            <Text style={styles.tipoTexto}>{tipo}</Text>
          </View>
        )}
      </View>
      <Text style={styles.quando}>{quando}</Text>
      <Text testID={`principal-${item.atividade_id}`} style={item.destaque ? styles.principalTexto : styles.principal}>
        {principal}
      </Text>
      <Text style={styles.meta}>{[item.destaque ? item.duracao : null, item.distancia].filter(Boolean).join(" · ")}</Text>
      {selo && (
        <View style={styles.selos}>
          <View testID={`selo-${selo.chave}-${item.atividade_id}`} style={[styles.selo, selo.atencao && styles.seloAtencao]}>
            <MaterialIcons name={selo.icone} size={tamanho.iconePequeno} color={selo.atencao ? tema.cor.alerta : tema.cor["texto-2"]} accessible={false} />
            <Text style={[styles.seloTexto, selo.atencao && { color: tema.cor.alerta }]}>{selo.texto}</Text>
          </View>
        </View>
      )}
    </Pressable>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { padding: espaco[4], gap: espaco[2], marginBottom: espaco[3], borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    topo: { flexDirection: "row", alignItems: "center", gap: espaco[2] },
    nome: { ...fonte["titulo-secao"], color: cor.texto, flex: 1 },
    tipo: { paddingHorizontal: espaco[2], paddingVertical: 2, borderRadius: raio.pilula, backgroundColor: cor["superficie-2"] },
    tipoTexto: { ...fonte.legenda, color: cor.texto },
    quando: { ...fonte.rotulo, color: cor["texto-2"] },
    principal: { ...fonte["numero-destaque"], color: cor.texto },
    principalTexto: { ...fonte["titulo-secao"], color: cor.texto },
    meta: { ...fonte.rotulo, color: cor["texto-2"] },
    selos: { flexDirection: "row", flexWrap: "wrap", gap: espaco[2], marginTop: espaco[1] },
    selo: { flexDirection: "row", alignItems: "center", gap: espaco[1], paddingHorizontal: espaco[2], paddingVertical: 4, borderRadius: raio.pilula, backgroundColor: cor["superficie-2"] },
    seloAtencao: { backgroundColor: cor["alerta-suave"] },
    seloTexto: { ...fonte.legenda, color: cor["texto-2"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
