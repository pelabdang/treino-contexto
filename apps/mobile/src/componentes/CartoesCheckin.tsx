// Cartões "Check-in" e "Carga pela PSE" da tela de um treino (#299, spec docs/design/telas/checkin.md).
// O app não calcula carga nem prazo: lê `checkin`, `carga_pse` e `checkin_aberto` do GET da atividade.
import { MaterialIcons } from "@expo/vector-icons";
import type { Atividade } from "@treino/api-client";
import { useMemo, useState } from "react";
import { AccessibilityInfo, Pressable, StyleSheet, Text, View } from "react-native";

import { apagarCheckin } from "../checkin/api";
import { avisoPrazoNoCartao, observacaoDoCheckin, pseDoCheckin } from "../checkin/escala";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";
import { Dialogo } from "./CheckinOpcoes";

type Props = {
  atividade: Atividade;
  apiUrl: string;
  atletaId: number;
  aoFazerCheckin: () => void;
  aoEditarCheckin: () => void;
  /** Depois de apagar: a tela do treino busca a atividade de novo. */
  aoApagado: () => void;
  fetchFn?: typeof fetch;
};

export function CartoesCheckin({ atividade, apiUrl, atletaId, aoFazerCheckin, aoEditarCheckin, aoApagado, fetchFn }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [dialogo, setDialogo] = useState(false);
  const [apagando, setApagando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const { checkin, carga_pse: carga } = atividade;
  const semCheckinElegivel = atividade.subtipo === "multiesporte_pai" || atividade.subtipo === "troca";
  // Tabela da spec: sem check-in e prazo fechado em treino inteiro ou troca = sem cartão.
  if (!checkin && !atividade.checkin_aberto && semCheckinElegivel) return null;

  const apagar = async () => {
    setDialogo(false);
    setErro(null);
    setApagando(true);
    const r = await apagarCheckin(atletaId, atividade.atividade_id, { baseUrl: apiUrl, fetch: fetchFn });
    setApagando(false);
    if (!r.ok) return setErro("Não foi possível apagar. Tente de novo.");
    setAviso("Check-in apagado.");
    try {
      AccessibilityInfo.announceForAccessibility?.("Check-in apagado.");
    } catch {
      // sem leitor de tela
    }
    aoApagado();
  };

  const obs = checkin ? observacaoDoCheckin(checkin) : null;
  return (
    <>
      <View testID="cartao-checkin" style={styles.cartao}>
        <Text accessibilityRole="header" style={styles.cartaoTitulo}>
          Check-in
        </Text>
        {checkin && obs ? (
          <>
            <Linha styles={styles} rotulo="Esforço (PSE)" valor={pseDoCheckin(checkin)} />
            <Linha styles={styles} rotulo="Sensação" valor={checkin.sensacao_texto} />
            <Linha styles={styles} rotulo="Observação" valor={obs.linha} />
            {obs.texto ? <Text style={styles.corpo}>{obs.texto}</Text> : null}
            {erro && (
              <Text accessibilityRole="alert" style={styles.erro}>
                {erro}
              </Text>
            )}
            <View style={styles.acoes}>
              <Pressable
                testID="editar-checkin"
                accessibilityRole="button"
                disabled={apagando}
                onPress={aoEditarCheckin}
                style={[styles.botaoSecundario, { flex: 2 }]}
              >
                <MaterialIcons name="edit" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
                <Text style={styles.botaoSecundarioTexto}>Editar</Text>
              </Pressable>
              <Pressable
                testID="apagar-checkin"
                accessibilityRole="button"
                disabled={apagando}
                onPress={() => setDialogo(true)}
                style={[styles.botaoTexto, { flex: 3, paddingHorizontal: espaco[2] }]}
              >
                <Text style={[styles.botaoSecundarioTexto, { color: tema.cor.erro }]}>{apagando ? "Apagando..." : "Apagar check-in"}</Text>
              </Pressable>
            </View>
          </>
        ) : (
          <>
            {aviso && (
              <Text accessibilityLiveRegion="polite" style={styles.sucesso}>
                {aviso}
              </Text>
            )}
            <View style={styles.nota}>
              <MaterialIcons name="assignment" size={tamanho.iconeMedio} color={tema.cor.texto} accessible={false} />
              <Text style={styles.notaTexto}>Você ainda não fez o check-in deste treino.</Text>
            </View>
            {carga?.estado === "sem_checkin" && <Text style={styles.secundario}>{carga.texto}</Text>}
            {atividade.checkin_aberto ? (
              <Pressable testID="fazer-checkin" accessibilityRole="button" onPress={aoFazerCheckin} style={styles.botaoPrimario}>
                <Text style={styles.botaoPrimarioTexto}>Fazer check-in</Text>
              </Pressable>
            ) : (
              <View testID="aviso-prazo" style={styles.nota}>
                <MaterialIcons name="info-outline" size={tamanho.iconeMedio} color={tema.cor.texto} accessible={false} />
                <Text style={styles.notaTexto}>{avisoPrazoNoCartao()}</Text>
              </View>
            )}
          </>
        )}
      </View>

      {checkin && carga && carga.estado !== "sem_checkin" && (
        <View testID="cartao-carga-pse" style={styles.cartao}>
          <Text accessibilityRole="header" style={styles.cartaoTitulo}>
            Carga pela PSE
          </Text>
          {carga.estado === "calculada" && carga.valor_texto ? <Text style={styles.destaque}>{carga.valor_texto}</Text> : null}
          <Text style={styles.secundario}>{carga.texto}</Text>
          {carga.estado === "calculada" && (
            <Text style={styles.legenda}>Não se compara com a carga do relógio (pontos): são escalas diferentes.</Text>
          )}
        </View>
      )}

      <Dialogo
        visivel={dialogo}
        titulo="Apagar este check-in?"
        texto="A PSE, a sensação e a observação deste treino serão apagadas. Isso não pode ser desfeito."
        primaria={{ rotulo: "Cancelar", aoPress: () => setDialogo(false) }}
        secundaria={{ rotulo: "Apagar", aoPress: () => void apagar(), perigo: true }}
        aoFechar={() => setDialogo(false)}
      />
    </>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function Linha({ styles, rotulo, valor }: { styles: Estilos; rotulo: string; valor: string }) {
  return (
    <View accessible accessibilityLabel={`${rotulo}, ${valor}`} style={styles.linha}>
      <Text style={styles.rotuloLinha}>{rotulo}</Text>
      <Text style={styles.valorLinha}>{valor}</Text>
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
    cartaoTitulo: { ...fonte["titulo-secao"], color: cor.texto },
    corpo: { ...fonte.corpo, color: cor.texto },
    secundario: { ...fonte.corpo, color: cor["texto-2"] },
    legenda: { ...fonte.legenda, color: cor["texto-2"] },
    destaque: { ...fonte["numero-destaque"], color: cor.texto },
    sucesso: { ...fonte.corpo, color: cor.sucesso },
    erro: { ...fonte.corpo, color: cor.erro },
    nota: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2] },
    notaTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    linha: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      gap: espaco[3],
      minHeight: 44,
      borderBottomWidth: borda.fina,
      borderBottomColor: cor.borda,
    },
    rotuloLinha: { ...fonte.corpo, color: cor["texto-2"] },
    valorLinha: { ...fonte["corpo-forte"], color: cor.texto, flexShrink: 1, textAlign: "right" },
    acoes: { flexDirection: "row", gap: espaco[2], marginTop: espaco[2] },
    botaoPrimario: { ...botao, backgroundColor: cor.destaque, alignSelf: "stretch" },
    botaoPrimarioTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    botaoSecundario: { ...botao, borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    botaoSecundarioTexto: { ...fonte.botao, color: cor.texto },
    botaoTexto: botao,
  });
}
