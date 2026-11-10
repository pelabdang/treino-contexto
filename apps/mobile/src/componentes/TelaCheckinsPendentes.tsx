// Lista de treinos sem check-in (#299, spec docs/design/telas/checkin.md). Só o treino aparece: nada do check-in.
import { MaterialIcons } from "@expo/vector-icons";
import type { CheckinsPendentes, ErroApi } from "@treino/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { buscarCheckinsPendentes } from "../checkin/api";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";
import { EsqueletoPendentes } from "./Esqueleto";
import { dataCurta } from "./GraficoTiros";
import { MODALIDADES } from "./modalidades";

type Props = {
  apiUrl: string;
  atletaId: number;
  /** Abre o check-in do treino (a rota leva só o id). */
  aoAbrirCheckin: (atividadeId: number) => void;
  aoVoltar?: () => void;
  /** Muda quando a tela volta ao foco: busca a lista de novo, sem apagar o que já está na tela. */
  atualizar?: number;
  fetchFn?: typeof fetch;
};

type Estado = { tipo: "carregando" } | { tipo: "ok"; dados: CheckinsPendentes } | { tipo: "erro"; erro: ErroApi };

export function TelaCheckinsPendentes({ apiUrl, atletaId, aoAbrirCheckin, aoVoltar, atualizar = 0, fetchFn }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let ativo = true;
    buscarCheckinsPendentes(atletaId, undefined, { baseUrl: apiUrl, fetch: fetchFn }).then((r) => {
      if (!ativo) return;
      // Um erro numa atualização em segundo plano não apaga a lista que já está na tela.
      setEstado((atual) => (r.ok ? { tipo: "ok", dados: r.dados } : atual.tipo === "ok" ? atual : { tipo: "erro", erro: r.erro }));
    });
    return () => {
      ativo = false;
    };
  }, [apiUrl, atletaId, fetchFn, tentativa, atualizar]);

  const tentarDeNovo = useCallback(() => {
    setEstado({ tipo: "carregando" });
    setTentativa((n) => n + 1);
  }, []);

  return (
    <ScrollView testID="rolagem-tela" contentContainerStyle={styles.container}>
      {aoVoltar && (
        <Pressable accessibilityRole="button" accessibilityLabel="Voltar" onPress={aoVoltar} style={styles.voltar}>
          <MaterialIcons name="arrow-back" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
          <Text style={styles.voltarTexto}>Voltar</Text>
        </Pressable>
      )}
      <Text accessibilityRole="header" style={styles.titulo}>
        Check-ins pendentes
      </Text>

      {estado.tipo === "carregando" && (
        <View>
          <Text accessibilityLiveRegion="polite" style={[styles.texto, { marginTop: espaco[2] }]}>
            Carregando seus treinos...
          </Text>
          <EsqueletoPendentes />
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
            {estado.erro.tipo === "rede"
              ? "Não foi possível falar com o servidor"
              : "Não foi possível carregar os pendentes. Tente de novo mais tarde."}
          </Text>
          {estado.erro.tipo === "rede" && (
            <Pressable accessibilityRole="button" onPress={tentarDeNovo} style={styles.botao}>
              <Text style={styles.botaoTexto}>Tentar de novo</Text>
            </Pressable>
          )}
        </View>
      )}

      {estado.tipo === "ok" && estado.dados.pendentes.length === 0 && (
        <View testID="estado-vazio" style={styles.estado}>
          <MaterialIcons name="check-circle-outline" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
          <Text accessibilityRole="header" style={styles.estadoTitulo}>
            Nenhum check-in pendente
          </Text>
          <Text style={styles.textoCentro}>Você fez o check-in de todos os treinos dos últimos {estado.dados.dias} dias.</Text>
        </View>
      )}

      {estado.tipo === "ok" && estado.dados.pendentes.length > 0 && (
        <View>
          <Text style={[styles.texto, { marginTop: espaco[2] }]}>Treinos dos últimos {estado.dados.dias} dias sem check-in</Text>
          <View testID="lista-pendentes" style={styles.cartao}>
            {estado.dados.pendentes.map((p, i) => {
              const mod = MODALIDADES[p.modalidade];
              const quando = `${dataCurta(p.data_local)} às ${p.hora_local}`;
              return (
                <Pressable
                  key={p.atividade_id}
                  testID={`pendente-${p.atividade_id}`}
                  accessibilityRole="button"
                  accessibilityLabel={`${p.titulo}, ${quando}`}
                  onPress={() => aoAbrirCheckin(p.atividade_id)}
                  style={[styles.linha, i > 0 && styles.linhaDivisor]}
                >
                  {mod && <MaterialIcons name={mod.icone} size={tamanho.iconeGrande} color={tema.cor[mod.cor]} accessible={false} />}
                  <View style={styles.linhaTextos}>
                    <Text style={styles.linhaTitulo}>{p.titulo}</Text>
                    <Text style={styles.texto}>{quando}</Text>
                  </View>
                  <MaterialIcons name="chevron-right" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
                </Pressable>
              );
            })}
          </View>
          <Text testID="total-pendentes" style={styles.legenda}>
            {estado.dados.total === 1 ? "1 treino sem check-in" : `${estado.dados.total} treinos sem check-in`}
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

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
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    textoCentro: { ...fonte.corpo, color: cor["texto-2"], textAlign: "center" },
    legenda: { ...fonte.legenda, color: cor["texto-2"], marginTop: espaco[2] },
    estado: { alignItems: "center", paddingVertical: espaco[7], gap: espaco[2] },
    estadoTitulo: { ...fonte["titulo-secao"], color: cor.texto },
    erro: { ...fonte.corpo, color: cor.erro, textAlign: "center", marginBottom: espaco[3] },
    botao: {
      minHeight: tamanho.botaoAltura,
      justifyContent: "center",
      paddingHorizontal: espaco[4],
      borderRadius: raio.medio,
      backgroundColor: cor.destaque,
    },
    botaoTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    cartao: {
      marginTop: espaco[3],
      borderRadius: raio.grande,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    linha: { minHeight: 72, flexDirection: "row", alignItems: "center", gap: espaco[3], paddingHorizontal: espaco[4] },
    linhaDivisor: { borderTopWidth: borda.fina, borderTopColor: cor.borda },
    linhaTextos: { flex: 1 },
    linhaTitulo: { ...fonte["corpo-forte"], color: cor.texto },
  });
}
