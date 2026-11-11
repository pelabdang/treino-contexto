// Cartão "Feedback" da tela de um treino (#330, spec docs/design/telas/feedback.md, ADR 0013).
// O app só mostra o que o GET da atividade manda: não gera, não corta e não confere o texto, não olha o `motivo`
// e não guarda nada (nem log, nem URL, nem armazenamento): é dado de saúde derivado do check-in.
import { MaterialIcons } from "@expo/vector-icons";
import type { EstadoFeedback, FeedbackTreino } from "@treino/api-client";
import { useMemo, useState } from "react";
import { AccessibilityInfo, Pressable, StyleSheet, Text, View } from "react-native";

import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

export const ORIGEM_AUTOMATICO = "Gerado automaticamente a partir dos dados deste treino e do seu check-in.";
export const ORIGEM_TESTE = "Texto de teste, gerado sem o provedor de verdade. Não é um feedback de verdade.";

/** Frases de reserva, só para quando a API não manda a `mensagem` (spec, tabela de estados). */
const RESERVA: Record<Exclude<EstadoFeedback, "pronto">, string> = {
  sem_checkin: "Faça o check-in para ver o feedback.",
  pendente: "O feedback deste treino ainda não foi gerado. Toque em Atualizar para ver se já está pronto.",
  desatualizado: "Você editou o check-in. O feedback será refeito.",
  indisponivel: "Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde.",
};
const RESERVA_PRAZO = "O prazo do check-in deste treino acabou, então ele fica sem feedback.";

type Props = {
  /** `null`, `undefined` ou atividade sem o campo: o cartão não aparece. */
  feedback: FeedbackTreino | null | undefined;
  /** "Fazer check-in" (só `sem_checkin` com prazo aberto). Sem a função, o botão não aparece. */
  aoFazerCheckin?: () => void;
  /**
   * "Atualizar" (`pendente` e `desatualizado`): a tela busca a atividade de novo, sem apagar o que está na tela, e devolve
   * o feedback novo (ou `undefined` se a busca falhar). Sem a função, o botão não aparece.
   */
  aoAtualizar?: () => Promise<FeedbackTreino | null | undefined>;
};

export function CartaoFeedback({ feedback, aoFazerCheckin, aoAtualizar }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [atualizando, setAtualizando] = useState(false);
  if (!feedback) return null;

  const texto = feedback.estado === "pronto" && feedback.texto ? feedback.texto : null;
  const teste = texto !== null && feedback.origem === "teste";
  const estadoSemTexto = (feedback.estado === "pronto" ? "indisponivel" : feedback.estado) as Exclude<EstadoFeedback, "pronto">;
  const prazoVencido = feedback.estado === "sem_checkin" && feedback.checkin_aberto === false;
  const mensagem = feedback.mensagem || (prazoVencido ? RESERVA_PRAZO : RESERVA[estadoSemTexto]);
  const icone = estadoSemTexto === "sem_checkin" && !prazoVencido ? "assignment" : "info-outline";
  const podeAtualizar = !texto && (estadoSemTexto === "pendente" || estadoSemTexto === "desatualizado") && !!aoAtualizar;
  const podeFazerCheckin = !texto && estadoSemTexto === "sem_checkin" && feedback.checkin_aberto === true && !!aoFazerCheckin;

  const anunciar = (frase: string) => {
    try {
      AccessibilityInfo.announceForAccessibility?.(frase);
    } catch {
      // sem leitor de tela
    }
  };
  const atualizar = async () => {
    if (!aoAtualizar) return;
    setAtualizando(true);
    const novo = await aoAtualizar();
    setAtualizando(false);
    if (novo === undefined) anunciar("Não foi possível atualizar o feedback.");
    else anunciar(novo?.estado === "pronto" ? "Feedback pronto." : "O feedback ainda não está pronto.");
  };

  return (
    <View testID="cartao-feedback" accessibilityLabel="Feedback do treino" style={styles.cartao}>
      <View style={styles.titulo}>
        <Text accessibilityRole="header" style={styles.tituloTexto}>
          Feedback
        </Text>
        {teste && (
          <View testID="selo-teste" style={styles.selo}>
            <Text style={styles.seloTexto}>Texto de teste</Text>
          </View>
        )}
      </View>
      {texto ? (
        <>
          <Text testID="feedback-texto" selectable style={styles.texto}>
            {texto}
          </Text>
          <View style={styles.divisoria} />
          <Text testID="feedback-origem" style={styles.legenda}>
            {teste ? ORIGEM_TESTE : ORIGEM_AUTOMATICO}
          </Text>
        </>
      ) : (
        <>
          <View style={styles.nota}>
            <MaterialIcons name={icone} size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
            <Text testID="feedback-mensagem" style={styles.notaTexto}>
              {mensagem}
            </Text>
          </View>
          {podeFazerCheckin && (
            <Pressable
              testID="feedback-fazer-checkin"
              accessibilityRole="button"
              accessibilityLabel="Fazer check-in para ver o feedback"
              onPress={aoFazerCheckin}
              style={styles.botaoSecundario}
            >
              <Text style={styles.botaoTextoSecundario}>Fazer check-in</Text>
            </Pressable>
          )}
          {podeAtualizar && (
            <Pressable
              testID="feedback-atualizar"
              accessibilityRole="button"
              accessibilityState={{ disabled: atualizando }}
              disabled={atualizando}
              onPress={() => void atualizar()}
              style={styles.botaoTexto}
            >
              <MaterialIcons name="refresh" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
              <Text style={styles.botaoTextoDestaque}>{atualizando ? "Atualizando..." : "Atualizar"}</Text>
            </Pressable>
          )}
        </>
      )}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  const botao = {
    minHeight: tamanho.botaoAltura,
    flexDirection: "row",
    gap: espaco[1],
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: espaco[4],
    borderRadius: raio.medio,
  } as const;
  return StyleSheet.create({
    cartao: {
      marginTop: espaco[4],
      padding: espaco[4],
      gap: espaco[2],
      borderRadius: raio.grande,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    titulo: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: espaco[2] },
    tituloTexto: { ...fonte["titulo-secao"], color: cor.texto },
    selo: { paddingVertical: espaco[1], paddingHorizontal: espaco[3], borderRadius: raio.pilula, backgroundColor: cor["superficie-2"] },
    seloTexto: { ...fonte.rotulo, color: cor.texto },
    texto: { ...fonte.corpo, color: cor.texto, textAlign: "left", maxWidth: 640 },
    divisoria: { height: borda.fina, backgroundColor: cor.borda, marginTop: espaco[1] },
    legenda: { ...fonte.legenda, color: cor["texto-2"] },
    nota: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2] },
    notaTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    botaoSecundario: { ...botao, alignSelf: "stretch", borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    botaoTextoSecundario: { ...fonte.botao, color: cor.destaque },
    botaoTexto: { ...botao, alignSelf: "flex-start", paddingHorizontal: espaco[2] },
    botaoTextoDestaque: { ...fonte.botao, color: cor.destaque },
  });
}
