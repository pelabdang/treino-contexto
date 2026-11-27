// Cartão "Último treino" do início v3 (spec docs/design/telas/inicio-atleta-v3.md, seção 1): modalidade, dia e hora, número do treino,
// linha de apoio, selo de normal e o fecho (convite do check-in dentro do cartão, ou o começo do feedback).
import { MaterialIcons } from "@expo/vector-icons";
import type { Atividade } from "@treino/api-client";
import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { numeroDoTreino, linhaDeApoio, primeirasLinhas, seloDoNormal } from "../inicio/numero";
import { comFoco } from "../tema/foco";
import type { ItemTreino } from "../treinos/api";
import { ORIGEM_AUTOMATICO, ORIGEM_TESTE } from "./CartaoFeedback";
import { TIPOS } from "./CartaoTreino";
import { diaCurto } from "./datasInicio";
import { MODALIDADES } from "./modalidades";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Props = {
  item: ItemTreino;
  /** Detalhe do treino (feedback, linha de base, pace). Sem ele, o cartão mostra só o que a lista traz. */
  atividade: Atividade | null;
  /** Outros treinos esperando check-in (sem contar este). */
  outrosSemCheckin: number;
  aoAbrir: () => void;
  aoResponderCheckin: () => void;
};

export function CartaoUltimoTreino({ item, atividade, outrosSemCheckin, aoAbrir, aoResponderCheckin }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const mod = MODALIDADES[item.modalidade];
  const nome = mod?.nome ?? "Treino";
  const tipo = item.tipo_treino ? TIPOS[item.tipo_treino] : null;
  const numero = atividade ? numeroDoTreino(atividade) : { valor: item.duracao, unidade: null, rotulo: "Duração" };
  const apoio = atividade ? linhaDeApoio(atividade) : [item.distancia, item.duracao].filter(Boolean).join(" · ");
  const selo = atividade ? seloDoNormal(atividade) : null;
  const fb = atividade?.feedback ?? null;
  const convite = item.checkin_estado === "pendente" && (fb?.checkin_aberto ?? true) && fb?.estado !== "pronto";
  const quando = `${diaCurto(item.data_local)} às ${item.hora_local}`;
  const falado = [nome, tipo, quando, numero.rotulo, `${numero.valor}${numero.unidade ? ` ${numero.unidade}` : ""}`, apoio, selo?.texto].filter(Boolean).join(", ");

  return (
    <View testID="ultimo-treino" style={styles.cartao}>
      <Text style={styles.sobretitulo}>ÚLTIMO TREINO</Text>
      <Pressable testID="abrir-ultimo-treino" accessibilityRole="button" accessibilityLabel={falado} onPress={aoAbrir} style={comFoco(styles.corpo, styles.foco)}>
        <View style={styles.topo}>
          <View style={styles.icone}>{mod && <MaterialIcons name={mod.icone} size={tamanho.iconeGrande} color={tema.cor[mod.cor]} accessible={false} />}</View>
          <View style={styles.titulos}>
            <Text style={styles.nome}>{tipo ? `${nome} · ${tipo}` : nome}</Text>
            <Text style={styles.quando}>{quando}</Text>
          </View>
          <MaterialIcons name="chevron-right" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
        </View>
        <View style={styles.numeroLinha}>
          <Text testID="numero-treino" style={styles.numero}>
            {numero.valor}
          </Text>
          {numero.unidade ? <Text style={styles.unidade}>{numero.unidade}</Text> : null}
        </View>
        <Text style={styles.rotulo}>{numero.rotulo}</Text>
        {apoio ? <Text style={styles.apoio}>{apoio}</Text> : null}
        {selo && (
          <View testID={`selo-normal-${selo.tipo}`} style={[styles.selo, selo.tipo === "dentro" && styles.seloDentro, selo.tipo === "fora" && styles.seloFora]}>
            <MaterialIcons
              name={selo.tipo === "dentro" ? "check-circle-outline" : selo.tipo === "fora" ? "warning-amber" : "hourglass-empty"}
              size={tamanho.iconePequeno}
              color={selo.tipo === "fora" ? tema.cor.alerta : selo.tipo === "dentro" ? tema.cor.link : tema.cor["texto-2"]}
              accessible={false}
            />
            <Text style={[styles.seloTexto, selo.tipo === "fora" && { color: tema.cor.alerta }, selo.tipo === "dentro" && { color: tema.cor.link }]}>{selo.texto}</Text>
          </View>
        )}
      </Pressable>

      {convite && (
        <View testID="convite-checkin" style={styles.faixa}>
          <Text style={styles.faixaTexto}>Responda o check-in e receba o feedback deste treino.</Text>
          <Pressable testID="responder-checkin" accessibilityRole="button" onPress={aoResponderCheckin} style={comFoco(styles.botao, styles.foco)}>
            <Text style={styles.botaoTexto}>Responder o check-in (3 perguntas)</Text>
          </Pressable>
          {outrosSemCheckin > 0 && (
            <Text testID="outros-sem-checkin" style={styles.faixaMais}>
              {outrosSemCheckin === 1 ? "+ 1 treino sem check-in" : `+ ${outrosSemCheckin} treinos sem check-in`}
            </Text>
          )}
        </View>
      )}

      {fb?.estado === "pronto" && fb.texto ? (
        <View testID="feedback-resumo" style={styles.feedback}>
          <Text style={styles.sobretitulo}>FEEDBACK</Text>
          <Text numberOfLines={3} style={styles.feedbackTexto}>
            {primeirasLinhas(fb.texto)}
          </Text>
          <Text style={styles.origem}>{fb.origem === "teste" ? ORIGEM_TESTE : ORIGEM_AUTOMATICO}</Text>
          <Pressable testID="ler-feedback" accessibilityRole="button" onPress={aoAbrir} style={comFoco(styles.link, styles.foco)}>
            <Text style={styles.linkTexto}>Ler feedback completo</Text>
          </Pressable>
        </View>
      ) : fb && !convite && fb.mensagem ? (
        <View testID="feedback-estado" style={styles.feedback}>
          <Text style={styles.origem}>{fb.mensagem}</Text>
        </View>
      ) : null}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { padding: espaco[4], gap: espaco[2], borderRadius: raio["cartao-destaque"], borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    sobretitulo: { ...fonte.sobretitulo, color: cor["texto-2"] },
    corpo: { gap: espaco[1] },
    topo: { flexDirection: "row", alignItems: "center", gap: espaco[3], marginBottom: espaco[2] },
    icone: { width: 40, height: 40, borderRadius: raio.bloco, backgroundColor: cor["superficie-2"], alignItems: "center", justifyContent: "center" },
    titulos: { flex: 1 },
    nome: { ...fonte["titulo-cartao"], color: cor.texto },
    quando: { ...fonte.rotulo, color: cor["texto-2"] },
    numeroLinha: { flexDirection: "row", alignItems: "flex-end", gap: espaco[2] },
    numero: { ...fonte["numero-heroi"], color: cor.texto },
    unidade: { ...fonte.rotulo, color: cor["texto-2"], marginBottom: espaco[2] },
    rotulo: { ...fonte.rotulo, color: cor["texto-2"] },
    apoio: { ...fonte.corpo, color: cor.texto },
    selo: { flexDirection: "row", alignItems: "center", gap: espaco[1], alignSelf: "flex-start", minHeight: 28, paddingHorizontal: espaco[3], borderRadius: raio.pilula, backgroundColor: cor["superficie-2"], marginTop: espaco[2] },
    seloDentro: { backgroundColor: cor["marca-suave"] },
    seloFora: { backgroundColor: cor["alerta-suave"] },
    seloTexto: { ...fonte.legenda, color: cor["texto-2"] },
    faixa: { gap: espaco[2], padding: espaco[3], borderRadius: raio.bloco, backgroundColor: cor.marca },
    faixaTexto: { ...fonte["corpo-forte"], color: cor["sobre-marca"] },
    faixaMais: { ...fonte.rotulo, color: cor["sobre-marca"] },
    botao: { minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.botao, backgroundColor: cor["sobre-marca"] }, // dentro da faixa volt o botão é sempre tinta (no escuro `cor.botao` também é volt)
    botaoTexto: { ...fonte.botao, color: cor.marca, textAlign: "center" },
    feedback: { gap: espaco[2], paddingTop: espaco[2], borderTopWidth: borda.fina, borderTopColor: cor.borda },
    feedbackTexto: { ...fonte.corpo, color: cor.texto },
    origem: { ...fonte.legenda, color: cor["texto-2"] },
    link: { minHeight: tamanho.alvoMinimo, justifyContent: "center", alignSelf: "flex-start" },
    linkTexto: { ...fonte.botao, color: cor.link },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
