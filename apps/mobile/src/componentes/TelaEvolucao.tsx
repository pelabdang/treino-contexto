import { buscarEvolucaoTiros1km, type ErroApi, type EvolucaoTiros1km } from "@treino/api-client";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

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

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Evolução dos tiros de 1 km
      </Text>
      {estado.tipo === "carregando" && (
        <View style={styles.centro}>
          <ActivityIndicator />
          <Text style={styles.texto}>Carregando seus tiros...</Text>
        </View>
      )}
      {estado.tipo === "erro" && (
        <View>
          <Text style={styles.erro}>{mensagemErro(estado.erro)}</Text>
          {estado.erro.tipo === "rede" && (
            <Pressable accessibilityRole="button" onPress={tentarDeNovo} style={styles.botao}>
              <Text style={styles.botaoTexto}>Tentar de novo</Text>
            </Pressable>
          )}
        </View>
      )}
      {estado.tipo === "ok" && <Sucesso dados={estado.dados} />}
    </ScrollView>
  );
}

function Sucesso({ dados }: { dados: EvolucaoTiros1km }) {
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

const styles = StyleSheet.create({
  container: { padding: 24, backgroundColor: "#fff", flexGrow: 1 },
  titulo: { fontSize: 24, fontWeight: "700", marginBottom: 12, color: "#111" },
  centro: { alignItems: "center", paddingVertical: 24, gap: 8 },
  texto: { fontSize: 16, color: "#444" },
  erro: { fontSize: 16, color: "#b00020", marginBottom: 12 },
  botao: { alignSelf: "flex-start", paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8, backgroundColor: "#1b6ca8" },
  botaoTexto: { color: "#fff", fontWeight: "600" },
  lista: { marginTop: 16 },
  linha: { flexDirection: "row", flexWrap: "wrap", gap: 12, paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: "#eee" },
  celula: { fontSize: 14, color: "#222" },
  rodape: { marginTop: 24 },
  pequeno: { fontSize: 12, color: "#666" },
});
