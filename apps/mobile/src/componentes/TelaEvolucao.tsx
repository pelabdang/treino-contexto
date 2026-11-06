import { buscarEvolucaoTiros1km, type ErroApi, type EvolucaoTiros1km } from "@treino/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { MaterialIcons } from "@expo/vector-icons";
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import { BotaoEnviarFit } from "./BotaoEnviarFit";
import { EsqueletoEvolucao } from "./Esqueleto";
import {
  borda,
  espaco,
  fonte,
  larguraConteudoMax,
  larguraMargemGrande,
  raio,
  tamanho,
  useMargemTela,
  useTema,
  type Tema,
} from "../tema";
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
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
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

  const vazio = estado.tipo === "ok" && estado.dados.sessoes.length === 0;

  return (
    <ScrollView testID="rolagem-tela" contentContainerStyle={styles.container}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Evolução dos tiros de 1 km
      </Text>
      <BotaoEnviarFit
        apiUrl={apiUrl}
        atletaId={atletaId}
        fetchFn={fetchFn}
        aoEnviar={recarregar}
        variante={vazio ? "primario" : "secundario"}
      />
      {estado.tipo === "carregando" && (
        <View>
          <Text accessibilityLiveRegion="polite" style={styles.texto}>
            Carregando seus tiros...
          </Text>
          <EsqueletoEvolucao />
        </View>
      )}
      {estado.tipo === "erro" && (
        <View testID="estado-erro" style={styles.estado}>
          <MaterialIcons
            name={estado.erro.tipo === "rede" ? "wifi-off" : "error-outline"}
            size={tamanho.iconeEstado}
            color={tema.cor.erro}
            accessible={false}
          />
          <Text accessibilityRole="alert" style={styles.erro}>
            {mensagemErro(estado.erro)}
          </Text>
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
      {estado.tipo === "ok" && <Sucesso dados={estado.dados} styles={styles} tema={tema} />}
    </ScrollView>
  );
}

function Sucesso({ dados, styles, tema }: { dados: EvolucaoTiros1km; styles: Estilos; tema: Tema }) {
  // A API manda as sessões em ordem de data crescente: a última é o último treino.
  const ultima = dados.sessoes.at(-1);
  // A seleção é única: ponto do gráfico e linha da lista escolhem a mesma sessão.
  const [selecionadaId, setSelecionadaId] = useState<number | null>(null);
  const larga = useWindowDimensions().width >= larguraMargemGrande;
  return (
    <View>
      {dados.sessoes.length === 0 ? (
        <View testID="estado-vazio" style={styles.estado}>
          <MaterialIcons name="insert-chart-outlined" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
          <Text accessibilityRole="header" style={styles.estadoTitulo}>
            Ainda não há treinos de tiros de 1 km
          </Text>
          <Text style={styles.texto}>Envie o arquivo FIT de um treino com tiros para ver a evolução aqui.</Text>
        </View>
      ) : (
        <>
          {ultima && (
            <View testID="cartao-ultimo-treino" style={styles.cartao}>
              <Text style={styles.cartaoTitulo}>Último treino · {dataCurta(ultima.data)}</Text>
              <Text style={styles.rotulo}>Melhor tiro</Text>
              <Text style={styles.destaque}>
                {ultima.pace_melhor} <Text style={styles.unidade}>min/km</Text>
              </Text>
              <Text style={styles.corpo}>
                FC do melhor tiro: {ultima.fc_melhor_tiro === null ? "sem FC" : `${ultima.fc_melhor_tiro} bpm`}
              </Text>
              <Text style={styles.secundario}>
                Média dos tiros: {ultima.pace_medio} min/km · {ultima.n_tiros} tiros
              </Text>
            </View>
          )}
          <View style={styles.cartao}>
            <Text style={styles.cartaoTitulo}>Evolução</Text>
            <GraficoTiros dados={dados} selecionadaId={selecionadaId} aoSelecionar={setSelecionadaId} />
          </View>
          <View testID="lista-sessoes" style={styles.cartao}>
            <Text style={styles.cartaoTitulo}>Treinos</Text>
            {larga && (
              <View testID="cabecalho-lista" style={styles.cabecalhoLista}>
                <Text style={[styles.colunaTitulo, styles.colData]}>Data</Text>
                <Text style={[styles.colunaTitulo, styles.colPace]}>Melhor tiro</Text>
                <Text style={[styles.colunaTitulo, styles.colFc]}>FC do melhor tiro</Text>
                <Text style={[styles.colunaTitulo, styles.colunaMedia]}>Média dos tiros</Text>
              </View>
            )}
            {[...dados.sessoes].reverse().map((s) => {
              const selecionada = s.atividade_id === selecionadaId;
              return (
                <Pressable
                  key={s.atividade_id}
                  testID={`linha-sessao-${s.atividade_id}`}
                  accessibilityRole="button"
                  accessibilityState={{ selected: selecionada }}
                  accessibilityLabel={`Sessão de ${dataCurta(s.data)}, melhor tiro ${s.pace_melhor} min/km`}
                  onPress={() => setSelecionadaId(s.atividade_id)}
                  style={({ pressed }) => [
                    styles.linha,
                    (selecionada || pressed) && { backgroundColor: tema.cor["destaque-suave"] },
                  ]}
                >
                  <Text style={[styles.celula, larga && styles.colData]}>{dataCurta(s.data)}</Text>
                  <Text style={[styles.celula, larga && styles.colPace]}>{s.pace_melhor} min/km</Text>
                  <Text style={[styles.celula, larga && styles.colFc]}>
                    {s.fc_melhor_tiro === null ? "sem FC" : `${s.fc_melhor_tiro} bpm`}
                  </Text>
                  {larga ? (
                    <Text style={[styles.secundarioLinha, styles.colunaMedia]}>
                      {s.pace_medio} min/km · {s.n_tiros} tiros
                    </Text>
                  ) : (
                    <Text style={styles.secundarioLinha}>
                      média {s.pace_medio} · {s.n_tiros} tiros
                    </Text>
                  )}
                </Pressable>
              );
            })}
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

function criarEstilos({ cor }: Tema, margem: number = espaco[4]) {
  return StyleSheet.create({
    container: {
      padding: margem,
      backgroundColor: cor.fundo,
      flexGrow: 1,
      width: "100%",
      maxWidth: larguraConteudoMax + 2 * margem,
      alignSelf: "center",
    },
    titulo: { ...fonte["titulo-tela"], marginBottom: espaco[3], color: cor.texto },
    estado: { alignItems: "center", paddingVertical: espaco[7], gap: espaco[2] },
    estadoTitulo: { ...fonte["titulo-secao"], color: cor.texto, textAlign: "center" },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    erro: { ...fonte.corpo, color: cor.erro, textAlign: "center", marginBottom: espaco[3] },
    botao: {
      alignSelf: "flex-start",
      minHeight: tamanho.botaoAltura,
      justifyContent: "center",
      paddingHorizontal: espaco[4],
      borderRadius: raio.medio,
      backgroundColor: cor.destaque,
    },
    botaoTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    cartao: {
      marginTop: espaco[4],
      padding: espaco[4],
      borderRadius: raio.grande,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    cartaoTitulo: { ...fonte["titulo-secao"], color: cor.texto },
    rotulo: { ...fonte.rotulo, marginTop: espaco[2], color: cor["texto-2"] },
    destaque: { ...fonte["numero-destaque"], color: cor.texto },
    unidade: { ...fonte.corpo, color: cor["texto-2"] },
    corpo: { ...fonte.corpo, color: cor.texto },
    secundario: { ...fonte.corpo, color: cor["texto-2"] },
    secundarioLinha: { ...fonte.legenda, flexBasis: "100%", color: cor["texto-2"] },
    linha: {
      flexDirection: "row",
      flexWrap: "wrap",
      columnGap: espaco[3],
      minHeight: tamanho.listaLinhaAltura,
      alignItems: "center",
      paddingVertical: espaco[2],
      borderBottomWidth: borda.fina,
      borderBottomColor: cor.borda,
    },
    cabecalhoLista: { flexDirection: "row", columnGap: espaco[3], marginTop: espaco[3], paddingBottom: espaco[1] },
    colunaTitulo: { ...fonte.rotulo, color: cor["texto-2"] },
    colData: { width: 88 },
    colPace: { width: 120 },
    colFc: { width: 140 },
    colunaMedia: { flexBasis: 0, flexGrow: 1 },
    celula: { ...fonte.rotulo, fontVariant: ["tabular-nums"], color: cor.texto },
    rodape: { marginTop: espaco[5] },
    pequeno: { ...fonte.legenda, color: cor["texto-2"] },
  });
}
