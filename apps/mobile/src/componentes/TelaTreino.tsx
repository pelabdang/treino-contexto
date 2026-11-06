import { MaterialIcons } from "@expo/vector-icons";
import { buscarAtividade, type Atividade, type ClimaAtividade, type ErroApi } from "@treino/api-client";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";
import { dataCurta } from "./GraficoTiros";

type Props = {
  apiUrl: string;
  atletaId: number;
  atividadeId: number;
  /** Mostra o botão "Voltar" quando vier. */
  aoVoltar?: () => void;
  /** Troque nos testes. Padrão: o fetch global. */
  fetchFn?: typeof fetch;
};

type Estado = { tipo: "carregando" } | { tipo: "ok"; dados: Atividade } | { tipo: "erro"; erro: ErroApi };

const MODALIDADES: Record<
  string,
  { nome: string; icone: "directions-run" | "directions-bike" | "pool"; cor: "corrida" | "ciclismo" | "natacao" }
> = {
  corrida: { nome: "Corrida", icone: "directions-run", cor: "corrida" },
  ciclismo: { nome: "Ciclismo", icone: "directions-bike", cor: "ciclismo" },
  natacao: { nome: "Natação", icone: "pool", cor: "natacao" },
};

function mensagemErro(erro: ErroApi): string {
  switch (erro.tipo) {
    case "nao_encontrado":
      return erro.detalhe.detail === "atleta não encontrado" ? "Atleta não encontrado" : "Treino não encontrado";
    case "rede":
      return "Não foi possível falar com o servidor";
    default:
      return "Não foi possível carregar este treino. Tente de novo mais tarde.";
  }
}

/** Número com vírgula decimal, sem arredondar (a API manda o valor pronto para exibir). */
function numeroBr(n: number): string {
  return String(n).replace(".", ",");
}

/** Metros em km, só para exibir (a API manda `distancia_m`). */
function distanciaKm(metros: number): string {
  return (metros / 1000).toFixed(2).replace(".", ",");
}

export function TelaTreino({ apiUrl, atletaId, atividadeId, aoVoltar, fetchFn }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let ativo = true;
    buscarAtividade(atletaId, atividadeId, { baseUrl: apiUrl, fetch: fetchFn }).then((r) => {
      if (ativo) setEstado(r.ok ? { tipo: "ok", dados: r.dados } : { tipo: "erro", erro: r.erro });
    });
    return () => {
      ativo = false;
    };
  }, [apiUrl, atletaId, atividadeId, fetchFn, tentativa]);

  const tentarDeNovo = useCallback(() => {
    setEstado({ tipo: "carregando" });
    setTentativa((n) => n + 1);
  }, []);

  return (
    <ScrollView testID="rolagem-tela" contentContainerStyle={styles.container}>
      {aoVoltar && (
        <Pressable accessibilityRole="button" accessibilityLabel="Voltar" onPress={aoVoltar} style={styles.voltar}>
          <MaterialIcons name="arrow-back" size={tamanho.iconeMedio} color={tema.cor.destaque} />
          <Text style={styles.voltarTexto}>Voltar</Text>
        </Pressable>
      )}
      {estado.tipo === "carregando" && (
        <View style={styles.centro}>
          <ActivityIndicator color={tema.cor.destaque} />
          <Text style={styles.texto}>Carregando o treino...</Text>
        </View>
      )}
      {estado.tipo === "erro" && (
        <View>
          <View style={[styles.aviso, { backgroundColor: tema.cor["erro-suave"] }]} accessibilityLiveRegion="polite">
            <MaterialIcons name="error-outline" size={tamanho.iconeMedio} color={tema.cor.erro} />
            <Text style={[styles.avisoTexto, { color: tema.cor.erro }]}>{mensagemErro(estado.erro)}</Text>
          </View>
          {estado.erro.tipo === "rede" && (
            <Pressable accessibilityRole="button" onPress={tentarDeNovo} style={styles.botao}>
              <Text style={styles.botaoTexto}>Tentar de novo</Text>
            </Pressable>
          )}
        </View>
      )}
      {estado.tipo === "ok" && <Treino atividade={estado.dados} styles={styles} tema={tema} />}
    </ScrollView>
  );
}

function Treino({ atividade, styles, tema }: { atividade: Atividade; styles: Estilos; tema: Tema }) {
  const mod = MODALIDADES[atividade.modalidade];
  return (
    <View>
      <Text accessibilityRole="header" style={styles.titulo}>
        Treino
      </Text>
      <View style={styles.cabecalho}>
        {mod && (
          <View testID="chip-modalidade" style={styles.chip}>
            <MaterialIcons name={mod.icone} size={tamanho.iconePequeno} color={tema.cor[mod.cor]} />
            <Text style={styles.chipTexto}>{mod.nome}</Text>
          </View>
        )}
        <Text style={styles.subtitulo}>
          {dataCurta(atividade.data_local)} às {atividade.hora_local}
        </Text>
      </View>

      <View testID="cartao-resumo" style={styles.cartao}>
        <Text style={styles.rotulo}>Duração</Text>
        <Text style={styles.destaque}>{atividade.duracao}</Text>
        {atividade.distancia_m !== null && (
          <Text style={styles.corpo}>
            Distância: {distanciaKm(atividade.distancia_m)} <Text style={styles.secundario}>km</Text>
          </Text>
        )}
        {atividade.pace_medio != null && (
          <Text style={styles.corpo}>
            Pace médio: {atividade.pace_medio} <Text style={styles.secundario}>min/km</Text>
          </Text>
        )}
        <Text style={styles.secundario}>FC média: {atividade.fc_media === null ? "sem FC" : `${atividade.fc_media} bpm`}</Text>
      </View>

      {atividade.clima && <CartaoClima clima={atividade.clima} styles={styles} tema={tema} />}
    </View>
  );
}

function CartaoClima({ clima, styles, tema }: { clima: ClimaAtividade; styles: Estilos; tema: Tema }) {
  const valor = (n: number | null | undefined, unidade: string) => (n == null ? "sem dado" : `${numeroBr(n)} ${unidade}`);
  let corpo: ReactNode;
  switch (clima.estado) {
    case "ok":
      corpo = (
        <>
          <Linha styles={styles} rotulo="Temperatura" valor={valor(clima.temperatura_c, "°C")} />
          <Linha styles={styles} rotulo="Sensação térmica" valor={valor(clima.sensacao_c, "°C")} />
          <Linha styles={styles} rotulo="Umidade" valor={valor(clima.umidade_pct, "%")} />
          <Linha styles={styles} rotulo="Vento" valor={valor(clima.vento_kmh, "km/h")} />
          {clima.atribuicao ? <Text style={styles.atribuicao}>{clima.atribuicao}</Text> : null}
        </>
      );
      break;
    case "indoor":
      corpo = <Nota styles={styles} tema={tema} icone="info-outline" texto="Treino em ambiente fechado: não há clima para mostrar." />;
      break;
    case "sem_posicao":
      corpo = <Nota styles={styles} tema={tema} icone="info-outline" texto="O arquivo não tem posição, então não dá para buscar o clima." />;
      break;
    case "pendente":
      corpo = (
        <Nota
          styles={styles}
          tema={tema}
          icone="info-outline"
          texto="O clima deste treino ainda não chegou. Treinos recentes podem levar cerca de uma semana."
        />
      );
      break;
    case "falha":
      corpo = <Nota styles={styles} tema={tema} icone="warning-amber" alerta texto="Não foi possível obter o clima deste treino." />;
      break;
  }
  return (
    <View testID="cartao-clima" style={styles.cartao}>
      <Text style={styles.cartaoTitulo}>Clima</Text>
      {corpo}
    </View>
  );
}

function Linha({ styles, rotulo, valor }: { styles: Estilos; rotulo: string; valor: string }) {
  return (
    <View style={styles.linha}>
      <Text style={styles.rotuloLinha}>{rotulo}</Text>
      <Text style={styles.valorLinha}>{valor}</Text>
    </View>
  );
}

function Nota({
  styles,
  tema,
  icone,
  texto,
  alerta,
}: {
  styles: Estilos;
  tema: Tema;
  icone: "info-outline" | "warning-amber";
  texto: string;
  alerta?: boolean;
}) {
  const cor = alerta ? tema.cor.alerta : tema.cor.texto;
  return (
    <View style={[styles.aviso, alerta && { backgroundColor: tema.cor["alerta-suave"] }]}>
      <MaterialIcons name={icone} size={tamanho.iconeMedio} color={cor} />
      <Text style={[styles.avisoTexto, { color: cor }]}>{texto}</Text>
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
    voltar: { flexDirection: "row", alignItems: "center", gap: espaco[2], minHeight: tamanho.alvoMinimo, alignSelf: "flex-start" },
    voltarTexto: { ...fonte.botao, color: cor.destaque },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    cabecalho: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", columnGap: espaco[3], rowGap: espaco[2], marginTop: espaco[2] },
    chip: {
      flexDirection: "row",
      alignItems: "center",
      gap: espaco[1],
      height: 28,
      paddingHorizontal: espaco[3],
      borderRadius: raio.pilula,
      backgroundColor: cor["superficie-2"],
    },
    chipTexto: { ...fonte.rotulo, color: cor.texto },
    subtitulo: { ...fonte.corpo, color: cor["texto-2"] },
    centro: { alignItems: "center", paddingVertical: espaco[5], gap: espaco[2] },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    botao: {
      alignSelf: "flex-start",
      minHeight: tamanho.botaoAltura,
      justifyContent: "center",
      paddingHorizontal: espaco[4],
      marginTop: espaco[3],
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
    cartaoTitulo: { ...fonte["titulo-secao"], color: cor.texto, marginBottom: espaco[2] },
    rotulo: { ...fonte.rotulo, color: cor["texto-2"] },
    destaque: { ...fonte["numero-destaque"], color: cor.texto },
    corpo: { ...fonte.corpo, color: cor.texto },
    secundario: { ...fonte.corpo, color: cor["texto-2"] },
    linha: {
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      minHeight: 44,
      borderBottomWidth: borda.fina,
      borderBottomColor: cor.borda,
    },
    rotuloLinha: { ...fonte.corpo, color: cor["texto-2"] },
    valorLinha: { ...fonte["corpo-forte"], fontVariant: ["tabular-nums"], color: cor.texto },
    atribuicao: { ...fonte.legenda, marginTop: espaco[3], color: cor["texto-2"] },
    aviso: {
      flexDirection: "row",
      alignItems: "flex-start",
      gap: espaco[2],
      padding: espaco[3],
      borderRadius: raio.medio,
      backgroundColor: cor["superficie-2"],
    },
    avisoTexto: { ...fonte.corpo, flex: 1 },
  });
}
