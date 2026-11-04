import { buscarEvolucaoTiros1km, type ErroApi, type EvolucaoTiros1km } from "@treino/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { BotaoEnviarFit } from "./BotaoEnviarFit";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useTema, type Tema } from "../tema";
import { dataCurta, GraficoTiros } from "./GraficoTiros";

type Props = {
  apiUrl: string;
  atletaId: number;
  /** Troque nos testes. Padrão: o fetch global. */
  fetchFn?: typeof fetch;
};

type Estado =
  | { tipo: "carregando" }
  | { tipo: "ok"; dados: EvolucaoTiros1km }
  | { tipo: "erro"; erro: ErroApi };

function mensagemErro(erro: ErroApi): string {
  switch (erro.tipo) {
    case "nao_encontrado":
      return "Atleta não encontrado";
    case "rede":
      return "Não foi possível falar com o servidor";
    default:
      return "Não foi possível carregar os tiros. Tente de novo mais tarde.";
  }
}

export function TelaEvolucao({ apiUrl, atletaId, fetchFn }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let ativo = true;
    buscarEvolucaoTiros1km(atletaId, {}, { baseUrl: apiUrl, fetch: fetchFn }).then((r) => {
      if (ativo) setEstado(r.ok ? { tipo: "ok", dados: r.dados } : { tipo: "erro", erro: r.erro });
    });
    return () => {
      ativo = false;
    };
  }, [apiUrl, atletaId, fetchFn, tentativa]);

  const tentarDeNovo = useCallback(() => {
    setEstado({ tipo: "carregando" });
    setTentativa((n) => n + 1);
  }, []);

  // Depois de um envio com sucesso, busca a evolução de novo (sem esconder o que já está na tela).
  const recarregar = useCallback(() => setTentativa((n) => n + 1), []);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Evolução dos tiros de 1 km
      </Text>
      <BotaoEnviarFit apiUrl={apiUrl} atletaId={atletaId} fetchFn={fetchFn} aoEnviar={recarregar} />
      {estado.tipo === "carregando" && (
        <View style={styles.centro}>
          <ActivityIndicator color={tema.cor.destaque} />
          <Text style={styles.texto}>Carregando seus tiros...</Text>
        </View>
      )}
      {estado.tipo === "erro" && (
        <View>
          <Text style={styles.erro}>{mensagemErro(estado.erro)}</Text>
          {estado.erro.tipo === "rede" && (
            <Pressable
              accessibilityRole="button"
              onPress={tentarDeNovo}
              style={({ pressed }) => [styles.botao, pressed && { backgroundColor: tema.cor["destaque-pressionado"] }]}
            >
              <Text style={styles.botaoTexto}>Tentar de novo</Text>
            </Pressable>
          )}
        </View>
      )}
      {estado.tipo === "ok" && <Sucesso dados={estado.dados} styles={styles} />}
    </ScrollView>
  );
}

function Sucesso({ dados, styles }: { dados: EvolucaoTiros1km; styles: Estilos }) {
  return (
    <View>
      {dados.sessoes.length === 0 ? (
        <Text style={styles.texto}>Ainda não há treinos de tiros de 1 km.</Text>
      ) : (
        <>
          <GraficoTiros dados={dados} />
          <View testID="lista-sessoes" style={styles.lista}>
            {dados.sessoes.map((s) => (
              <View key={s.atividade_id} style={styles.linha}>
                <Text style={styles.celula}>{dataCurta(s.data)}</Text>
                <Text style={styles.celula}>{s.pace_medio} min/km</Text>
                <Text style={styles.celula}>{s.fc_media === null ? "sem FC" : `${s.fc_media} bpm`}</Text>
                <Text style={styles.celula}>{s.n_tiros} tiros</Text>
              </View>
            ))}
          </View>
        </>
      )}
      <View style={styles.rodape}>
        <Text style={styles.pequeno}>cálculo: {dados.versao_calculo}</Text>
        {dados.reclassificacao_pendente && <Text style={styles.pequeno}>cálculo em atualização</Text>}
      </View>
    </View>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    container: {
      padding: espaco[5],
      backgroundColor: cor.fundo,
      flexGrow: 1,
      width: "100%",
      maxWidth: larguraConteudoMax + 2 * espaco[5],
      alignSelf: "center",
    },
    titulo: { ...fonte["titulo-tela"], marginBottom: espaco[3], color: cor.texto },
    centro: { alignItems: "center", paddingVertical: espaco[5], gap: espaco[2] },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    erro: { ...fonte.corpo, color: cor.erro, marginBottom: espaco[3] },
    botao: {
      alignSelf: "flex-start",
      minHeight: tamanho.botaoAltura,
      justifyContent: "center",
      paddingHorizontal: espaco[4],
      borderRadius: raio.medio,
      backgroundColor: cor.destaque,
    },
    botaoTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    lista: { marginTop: espaco[4] },
    linha: {
      flexDirection: "row",
      flexWrap: "wrap",
      gap: espaco[3],
      paddingVertical: espaco[2],
      borderBottomWidth: borda.fina,
      borderBottomColor: cor.borda,
    },
    celula: { ...fonte.rotulo, fontVariant: ["tabular-nums"], color: cor.texto },
    rodape: { marginTop: espaco[5] },
    pequeno: { ...fonte.legenda, color: cor["texto-2"] },
  });
}
