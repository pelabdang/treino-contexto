// Início v3 do atleta (spec docs/design/telas/inicio-atleta-v3.md, seção 1): saudação, último treino (com o convite do check-in dentro),
// faixa de outro treino sem check-in, quinzena e treinos recentes. Cada cartão busca e falha sozinho ("Tentar de novo").
// Só mostra texto pronto da API; nada de saúde vai para log.
import { MaterialIcons } from "@expo/vector-icons";
import {
  buscarAtividade,
  buscarCarga,
  buscarCartoesInicio,
  type Atividade,
  type CartoesInicio,
  type OpcoesCliente,
  type Resultado,
  type SerieCarga,
} from "@treino/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import { buscarCheckinsPendentes } from "../checkin/api";
import { comFoco } from "../tema/foco";
import { buscarTreinos, type ItemTreino } from "../treinos/api";
import { BotaoEnviarFit } from "./BotaoEnviarFit";
import { CartaoQuinzena } from "./CartaoQuinzena";
import { CartaoTreino } from "./CartaoTreino";
import { CartaoUltimoTreino } from "./CartaoUltimoTreino";
import { diaCurto, hojePorExtenso } from "./datasInicio";
import { EntradaChat } from "./EntradaChat";
import { EsqueletoCartoes, EsqueletoPendentes } from "./Esqueleto";
import { LogoPulso } from "./LogoPulso";
import { MODALIDADES } from "./modalidades";
import { SecaoNumeros, type DestinoCartao } from "./SecaoNumeros";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  apiUrl: string;
  atletaId: number;
  /** Nome completo da sessão; a saudação usa o primeiro. */
  nome?: string;
  aoAbrirTreino: (atividadeId: number) => void;
  aoResponderCheckin: (atividadeId: number) => void;
  aoVerTodos: () => void;
  /** Toque num cartão de "Seus números": a Evolução (com a série), a semana-padrão ou um treino. Sem ele, a seção não aparece. */
  aoAbrirDestino?: (destino: DestinoCartao) => void;
  /** Entrada do chat "Pergunte ao seu treino" (#600). Sem ela, o bloco não aparece. */
  aoAbrirChat?: () => void;
  /** Muda quando a aba volta ao foco: tudo é buscado de novo. */
  atualizar?: number;
  fetchFn?: typeof fetch;
  agora?: () => Date;
};

type Busca<T> = { tipo: "carregando" } | { tipo: "erro"; rede: boolean } | { tipo: "ok"; dados: T };

/**
 * Uma busca que nunca lança. `entidade` identifica o que se busca (trocar zera o estado para "carregando"); `refresco` busca de novo
 * o mesmo, mantendo o que já está na tela se a nova busca falhar.
 */
function useBusca<T>(buscar: () => Promise<Resultado<T>>, entidade: string, refresco: unknown): [Busca<T>, () => void] {
  const [guardado, setGuardado] = useState<{ entidade: string; busca: Busca<T> }>({ entidade, busca: { tipo: "carregando" } });
  const [n, setN] = useState(0);
  useEffect(() => {
    let vivo = true;
    buscar().then((r) => {
      if (!vivo) return;
      setGuardado((atual) => {
        if (r.ok) return { entidade, busca: { tipo: "ok", dados: r.dados } };
        if (atual.entidade === entidade && atual.busca.tipo === "ok") return atual;
        return { entidade, busca: { tipo: "erro", rede: r.erro.tipo === "rede" } };
      });
    });
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entidade, refresco, n]);
  const recarregar = useCallback(() => {
    setGuardado((atual) => ({ ...atual, busca: { tipo: "carregando" } }));
    setN((v) => v + 1);
  }, []);
  return [guardado.entidade === entidade ? guardado.busca : { tipo: "carregando" }, recarregar];
}

const LARGURA_DUAS_COLUNAS = 900;

export function TelaInicio({ apiUrl, atletaId, nome, aoAbrirTreino, aoResponderCheckin, aoVerTodos, aoAbrirDestino, aoAbrirChat, atualizar = 0, fetchFn, agora = () => new Date() }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const larga = useWindowDimensions().width >= LARGURA_DUAS_COLUNAS;
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const opcoes: OpcoesCliente = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);

  const [lista, recarregarLista] = useBusca(() => buscarTreinos(atletaId, { limite: 5 }, opcoes), `lista-${atletaId}-${opcoes.baseUrl}`, atualizar);
  const [pendentes] = useBusca(() => buscarCheckinsPendentes(atletaId, 7, opcoes), `pendentes-${atletaId}-${opcoes.baseUrl}`, atualizar);
  const [quinzena, recarregarQuinzena] = useBusca<SerieCarga>(() => buscarCarga(atletaId, { ultimos: 14 }, opcoes), `quinzena-${atletaId}-${opcoes.baseUrl}`, atualizar);

  // Extras: se a busca falha, a seção some em silêncio (o erro do último treino e da quinzena continuam visíveis).
  const [numeros] = useBusca<CartoesInicio>(() => buscarCartoesInicio(atletaId, opcoes), `numeros-${atletaId}-${opcoes.baseUrl}`, atualizar);
  const cartoes = aoAbrirDestino && numeros.tipo === "ok" && Array.isArray(numeros.dados.cartoes) ? numeros.dados.cartoes : [];

  const itens = lista.tipo === "ok" ? (lista.dados.itens ?? []) : [];
  const ultimo = itens[0] ?? null;
  const [detalhe, recarregarDetalhe] = useBusca<Atividade | null>(
    () => (ultimo ? buscarAtividade(atletaId, ultimo.atividade_id, opcoes) : Promise.resolve({ ok: true as const, dados: null })),
    `detalhe-${ultimo?.atividade_id ?? "-"}-${opcoes.baseUrl}`,
    atualizar,
  );

  const pendentesLista = pendentes.tipo === "ok" ? (pendentes.dados.pendentes ?? []) : [];
  const outros = pendentesLista.filter((p) => p.atividade_id !== ultimo?.atividade_id);
  const ultimoPendente = ultimo?.checkin_estado === "pendente";
  const faixaOutro = !ultimoPendente ? outros[0] : null;

  const saudacao = nome ? `Olá, ${nome.trim().split(/\s+/)[0]}` : "Olá";

  const carregando = (
    <View>
      <Text accessibilityLiveRegion="polite" style={styles.texto}>
        Carregando
      </Text>
      <EsqueletoPendentes />
    </View>
  );
  const erro = (rede: boolean, tentar: () => void, testID: string) => (
    <View testID={testID} style={styles.cartaoErro}>
      <MaterialIcons name={rede ? "wifi-off" : "error-outline"} size={tamanho.iconeGrande} color={tema.cor.erro} accessible={false} />
      <Text accessibilityRole="alert" style={styles.erro}>
        Não foi possível carregar.
      </Text>
      <Pressable testID={`${testID}-tentar`} accessibilityRole="button" onPress={tentar} style={comFoco(styles.link, styles.foco)}>
        <Text style={styles.linkTexto}>Tentar de novo</Text>
      </Pressable>
    </View>
  );

  const semTreinos = lista.tipo === "ok" && itens.length === 0;

  // "Seus números": no celular entre a quinzena e os recentes; no computador na coluna do último treino.
  const numerosNaTela = aoAbrirDestino && numeros.tipo === "carregando" ? (
    <View testID="carregando-numeros">
      <Text style={styles.apenasLeitor}>Carregando seus números</Text>
      <EsqueletoCartoes />
    </View>
  ) : cartoes.length > 0 && aoAbrirDestino ? (
    <SecaoNumeros cartoes={cartoes} aoAbrir={aoAbrirDestino} />
  ) : null;

  const colunaUltimo = (
    <View style={[styles.coluna, larga && styles.colunaLarga]}>
      {lista.tipo === "carregando" && carregando}
      {lista.tipo === "erro" && erro(lista.rede, recarregarLista, "erro-ultimo")}
      {semTreinos && (
        <View testID="estado-vazio" style={styles.vazio}>
          <LogoPulso tamanho={56} />
          <Text accessibilityRole="header" style={styles.vazioTitulo}>
            Nenhum treino ainda. Envie o arquivo do seu relógio e a análise aparece aqui.
          </Text>
          <BotaoEnviarFit apiUrl={apiUrl} atletaId={atletaId} fetchFn={fetchFn} aoEnviar={recarregarLista} variante="primario" rotulo="Enviar arquivo FIT" />
        </View>
      )}
      {ultimo && (
        <>
          <CartaoUltimoTreino
            item={ultimo}
            atividade={detalhe.tipo === "ok" ? detalhe.dados : null}
            outrosSemCheckin={outros.length}
            aoAbrir={() => aoAbrirTreino(ultimo.atividade_id)}
            aoResponderCheckin={() => aoResponderCheckin(ultimo.atividade_id)}
          />
          {detalhe.tipo === "erro" && erro(detalhe.rede, recarregarDetalhe, "erro-detalhe")}
        </>
      )}
      {faixaOutro && (
        <View testID="faixa-outro-checkin" style={styles.faixa}>
          <View style={styles.faixaTextos}>
            <Text style={styles.faixaTitulo}>Como foi o {(MODALIDADES[faixaOutro.modalidade]?.nome ?? "treino").toLowerCase()}?</Text>
            <Text style={styles.faixaData}>{diaCurto(faixaOutro.data_local)}</Text>
          </View>
          <Pressable
            testID="responder-outro"
            accessibilityRole="button"
            accessibilityLabel={`Responder o check-in de ${faixaOutro.titulo}`}
            onPress={() => aoResponderCheckin(faixaOutro.atividade_id)}
            style={comFoco(styles.botao, styles.foco)}
          >
            <Text style={styles.botaoTexto}>Responder</Text>
          </Pressable>
        </View>
      )}
      {larga && numerosNaTela}
    </View>
  );

  const colunaOutros = (
    <View style={[styles.coluna, larga && styles.colunaLarga]}>
      {quinzena.tipo === "carregando" && carregando}
      {quinzena.tipo === "erro" && erro(quinzena.rede, recarregarQuinzena, "erro-quinzena")}
      {quinzena.tipo === "ok" && <CartaoQuinzena serie={quinzena.dados} />}
      {!larga && numerosNaTela}
      {itens.length > 1 && (
        <View testID="recentes" style={styles.recentes}>
          <Text accessibilityRole="header" style={styles.secao}>
            Treinos recentes
          </Text>
          {itens.slice(1, 5).map((i: ItemTreino) => (
            <CartaoTreino key={i.atividade_id} item={i} aoAbrir={() => aoAbrirTreino(i.atividade_id)} />
          ))}
          <Pressable testID="ver-todos" accessibilityRole="button" onPress={aoVerTodos} style={comFoco(styles.link, styles.foco)}>
            <Text style={styles.linkTexto}>Ver todos</Text>
          </Pressable>
        </View>
      )}
    </View>
  );

  return (
    <ScrollView testID="tela-inicio" contentContainerStyle={styles.container}>
      <View style={styles.saudacao}>
        <LogoPulso tamanho={40} />
        <View>
          <Text accessibilityRole="header" style={styles.titulo}>
            {saudacao}
          </Text>
          <Text testID="data-hoje" style={styles.data}>
            {hojePorExtenso(agora())}
          </Text>
        </View>
      </View>
      {aoAbrirChat && <EntradaChat aoAbrir={aoAbrirChat} />}
      <View style={[styles.colunas, larga && styles.colunasLarga]}>
        {colunaUltimo}
        {colunaOutros}
      </View>
    </ScrollView>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    container: { padding: margem, alignSelf: "center", width: "100%", maxWidth: 2 * larguraConteudoMax + 2 * margem, gap: espaco[4], flexGrow: 1 },
    saudacao: { flexDirection: "row", alignItems: "center", gap: espaco[3] },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    data: { ...fonte.rotulo, color: cor["texto-2"] },
    colunas: { gap: espaco[4] },
    colunasLarga: { flexDirection: "row", alignItems: "flex-start" },
    coluna: { gap: espaco[3], width: "100%" },
    colunaLarga: { flex: 1, width: "auto" },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    apenasLeitor: { position: "absolute", width: 1, height: 1, opacity: 0 },
    secao: { ...fonte["titulo-secao"], color: cor.texto },
    recentes: { gap: espaco[1] },
    vazio: { alignItems: "center", gap: espaco[3], paddingVertical: espaco[6] },
    vazioTitulo: { ...fonte["titulo-secao"], color: cor.texto, textAlign: "center" },
    cartaoErro: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: espaco[2], padding: espaco[4], borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    erro: { ...fonte.corpo, color: cor.erro, flex: 1 },
    link: { minHeight: tamanho.alvoMinimo, justifyContent: "center", alignSelf: "flex-start" },
    linkTexto: { ...fonte.botao, color: cor.link },
    faixa: { flexDirection: "row", alignItems: "center", gap: espaco[3], padding: espaco[3], borderRadius: raio.bloco, backgroundColor: cor.marca },
    faixaTextos: { flex: 1 },
    faixaTitulo: { ...fonte["corpo-forte"], color: cor["sobre-marca"] },
    faixaData: { ...fonte.rotulo, color: cor["sobre-marca"] },
    botao: { minHeight: tamanho.botaoAltura, justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.botao, backgroundColor: cor["sobre-marca"] }, // dentro da faixa volt o botão é sempre tinta (no escuro `cor.botao` também é volt)
    botaoTexto: { ...fonte.botao, color: cor.marca, textAlign: "center" },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
