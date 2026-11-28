// Início v5 do atleta (spec docs/design/telas/inicio-v5-direcoes.md, "Spec final"): saudação, cartão grande de check-in (só com pendência), "Esta semana",
// chat "Pergunte ao seu treino", hoje e último treino ou "Check-ins em dia" (sem pendência) e, abaixo da dobra, quinzena, "Seus números" e treinos recentes.
// Cada busca falha sozinha. O app não calcula: só mostra texto pronto da API ou fixo.
// Só mostra texto pronto da API; nada de saúde vai para log.
import { MaterialIcons } from "@expo/vector-icons";
import {
  buscarCarga,
  buscarCartoesInicio,
  type CartoesInicio,
  type OpcoesCliente,
  type Resultado,
  type SerieCarga,
} from "@treino/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { PROFESSOR_NO_INICIO } from "../chat/textos";
import { buscarCheckinsPendentes } from "../checkin/api";
import { comFoco } from "../tema/foco";
import { buscarTreinos, type ItemTreino } from "../treinos/api";
import { BotaoEnviarFit } from "./BotaoEnviarFit";
import { CartaoQuinzena } from "./CartaoQuinzena";
import { CartaoTreino } from "./CartaoTreino";
import { BlocoSemana } from "./BlocoSemana";
import { CartaoCheckinGrande } from "./CartaoCheckinGrande";
import { ChatNoInicio } from "./ChatNoInicio";
import { diaCurto, hojePorExtenso } from "./datasInicio";
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
  /** Treinos sem check-in (a lista da aba Treinos já filtrada). */
  aoVerPendentes?: () => void;
  /** Toque num cartão de "Seus números" ou em "Esta semana": a Evolução (com a série), a semana-padrão ou um treino. Sem ele, esses blocos não aparecem. */
  aoAbrirDestino?: (destino: DestinoCartao) => void;
  /** Chat (Início v5, item 4): sem `aoAbrirChat` o bloco não aparece. `aoPerguntar` recebe o índice em `PERGUNTAS_PRONTAS`. */
  aoAbrirChat?: () => void;
  aoPerguntar?: (indice: number) => void;
  aoAbrirConversas?: () => void;
  /** "Seu professor" (Meta 15): só aparece com `PROFESSOR_NO_INICIO` ligado e o dado vindo da API. */
  professor?: { texto: string; aoAbrir: () => void };
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

const IDS_NO_TOPO = ["esta_semana", "hoje_na_semana"];

export function TelaInicio({ apiUrl, atletaId, nome, aoAbrirTreino, aoResponderCheckin, aoVerTodos, aoVerPendentes, aoAbrirDestino, aoAbrirChat, aoPerguntar, aoAbrirConversas, professor, atualizar = 0, fetchFn, agora = () => new Date() }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const opcoes: OpcoesCliente = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);

  const [lista, recarregarLista] = useBusca(() => buscarTreinos(atletaId, { limite: 5 }, opcoes), `lista-${atletaId}-${opcoes.baseUrl}`, atualizar);
  const [pendentes] = useBusca(() => buscarCheckinsPendentes(atletaId, 7, opcoes), `pendentes-${atletaId}-${opcoes.baseUrl}`, atualizar);
  const [quinzena, recarregarQuinzena] = useBusca<SerieCarga>(() => buscarCarga(atletaId, { ultimos: 14 }, opcoes), `quinzena-${atletaId}-${opcoes.baseUrl}`, atualizar);
  // Extras: se a busca falha, o bloco some em silêncio (o erro do último treino e da quinzena continuam visíveis).
  const [numeros] = useBusca<CartoesInicio>(() => buscarCartoesInicio(atletaId, opcoes), `numeros-${atletaId}-${opcoes.baseUrl}`, atualizar);

  const todosCartoes = aoAbrirDestino && numeros.tipo === "ok" && Array.isArray(numeros.dados.cartoes) ? numeros.dados.cartoes : [];
  const semana = todosCartoes.find((c) => c.id === "esta_semana");
  const hoje = todosCartoes.find((c) => c.id === "hoje_na_semana");
  const cartoes = todosCartoes.filter((c) => !IDS_NO_TOPO.includes(c.id));

  const itens = lista.tipo === "ok" ? (lista.dados.itens ?? []) : [];
  const ultimo = itens[0] ?? null;
  const pendentesLista = pendentes.tipo === "ok" ? (pendentes.dados.pendentes ?? []) : [];
  const pendente = pendentesLista[0] ?? null;
  // Sem a resposta dos pendentes ainda (ou com erro), nenhum dos dois estados de check-in aparece: não se afirma o que não se sabe.
  const checkinsConhecidos = pendentes.tipo === "ok";
  const emDia = checkinsConhecidos && !pendente;

  const saudacao = nome ? `Olá, ${nome.trim().split(/\s+/)[0]}` : "Olá";
  const semTreinos = lista.tipo === "ok" && itens.length === 0;

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

  const modUltimo = ultimo ? MODALIDADES[ultimo.modalidade] : undefined;
  const abrirUltimo = () => ultimo && aoAbrirTreino(ultimo.atividade_id);

  return (
    <ScrollView testID="tela-inicio" contentContainerStyle={styles.container}>
      <View style={styles.coluna}>
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

        {lista.tipo === "carregando" && carregando}
        {lista.tipo === "erro" && erro(lista.rede, recarregarLista, "erro-ultimo")}

        {pendente && (
          <CartaoCheckinGrande treino={pendente} outros={pendentesLista.length - 1} aoResponder={() => aoResponderCheckin(pendente.atividade_id)} aoVerOutros={aoVerPendentes ?? aoVerTodos} />
        )}

        {semana && aoAbrirDestino && <BlocoSemana cartao={semana} heroi={emDia} aoAbrir={aoAbrirDestino} />}

        {aoAbrirChat && aoPerguntar && aoAbrirConversas && (
          <ChatNoInicio aoAbrirChat={aoAbrirChat} aoPerguntar={aoPerguntar} aoAbrirConversas={aoAbrirConversas} semProntas={semTreinos} />
        )}

        {semTreinos && (
          <View testID="estado-vazio" style={styles.vazio}>
            <LogoPulso tamanho={56} />
            <Text accessibilityRole="header" style={styles.vazioTitulo}>
              Nenhum treino ainda. Envie o arquivo do seu relógio e a análise aparece aqui.
            </Text>
            <BotaoEnviarFit apiUrl={apiUrl} atletaId={atletaId} fetchFn={fetchFn} aoEnviar={recarregarLista} variante="primario" rotulo="Enviar arquivo FIT" />
          </View>
        )}

        {emDia && ultimo && (
          <View testID="hoje-e-ultimo" style={styles.par}>
            {hoje && aoAbrirDestino && (
              <Pressable testID="bloco-hoje" accessibilityRole="button" accessibilityLabel={hoje.rotulo_acessivel} onPress={() => aoAbrirDestino(hoje.destino)} style={comFoco([styles.metade, styles.cartaoPequeno], styles.foco)}>
                <Text style={styles.sobretitulo}>{hoje.rotulo.toUpperCase()}</Text>
                <Text style={styles.valorPequeno}>{hoje.valor}</Text>
                {hoje.apoio ? <Text style={styles.apoioPequeno}>{hoje.apoio}</Text> : null}
              </Pressable>
            )}
            <Pressable testID="abrir-ultimo-treino" accessibilityRole="button" accessibilityLabel={`Último treino, ${ultimo.duracao}, ${modUltimo?.nome ?? "treino"}, ${diaCurto(ultimo.data_local)}`} onPress={abrirUltimo} style={comFoco([styles.metade, styles.cartaoPequeno], styles.foco)}>
              <Text style={styles.sobretitulo}>ÚLTIMO TREINO</Text>
              <Text testID="numero-treino" style={styles.valorPequeno}>{ultimo.duracao}</Text>
              <Text style={styles.apoioPequeno}>{`${modUltimo?.nome ?? "Treino"} · ${diaCurto(ultimo.data_local)}`}</Text>
            </Pressable>
          </View>
        )}

        {emDia && ultimo && (
          <View testID="checkins-em-dia" style={styles.emDia}>
            <Text style={styles.emDiaTexto}>✓ Check-ins em dia</Text>
            <Pressable testID="ver-feedback" accessibilityRole="button" onPress={abrirUltimo} style={comFoco(styles.link, styles.foco)}>
              <Text style={styles.linkTexto}>Ver feedback ›</Text>
            </Pressable>
          </View>
        )}

        {PROFESSOR_NO_INICIO && professor && (
          <Pressable testID="linha-professor" accessibilityRole="button" onPress={professor.aoAbrir} style={comFoco(styles.emDia, styles.foco)}>
            <Text style={styles.sobretitulo}>SEU PROFESSOR</Text>
            <Text style={styles.emDiaTexto}>{professor.texto}</Text>
          </Pressable>
        )}

        {/* Abaixo da dobra, como na v4: quinzena, "Seus números" e treinos recentes. */}
        {quinzena.tipo === "carregando" && carregando}
        {quinzena.tipo === "erro" && erro(quinzena.rede, recarregarQuinzena, "erro-quinzena")}
        {quinzena.tipo === "ok" && <CartaoQuinzena serie={quinzena.dados} />}
        {aoAbrirDestino && numeros.tipo === "carregando" ? (
          <View testID="carregando-numeros">
            <Text style={styles.apenasLeitor}>Carregando seus números</Text>
            <EsqueletoCartoes />
          </View>
        ) : cartoes.length > 0 && aoAbrirDestino ? (
          <SecaoNumeros cartoes={cartoes} aoAbrir={aoAbrirDestino} />
        ) : null}
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
    </ScrollView>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    container: { padding: margem, alignItems: "center", flexGrow: 1 },
    coluna: { width: "100%", maxWidth: larguraConteudoMax, gap: espaco[4] },
    saudacao: { flexDirection: "row", alignItems: "center", gap: espaco[3] },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    data: { ...fonte.rotulo, color: cor["texto-2"] },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    apenasLeitor: { position: "absolute", width: 1, height: 1, opacity: 0 },
    secao: { ...fonte["titulo-secao"], color: cor.texto },
    sobretitulo: { ...fonte.sobretitulo, color: cor["texto-2"] },
    recentes: { gap: espaco[1] },
    vazio: { alignItems: "center", gap: espaco[3], paddingVertical: espaco[6] },
    vazioTitulo: { ...fonte["titulo-secao"], color: cor.texto, textAlign: "center" },
    cartaoErro: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: espaco[2], padding: espaco[4], borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    erro: { ...fonte.corpo, color: cor.erro, flex: 1 },
    link: { minHeight: tamanho.alvoMinimo, justifyContent: "center", alignSelf: "flex-start" },
    linkTexto: { ...fonte.botao, color: cor.link },
    par: { flexDirection: "row", gap: espaco[3] },
    metade: { flex: 1 },
    cartaoPequeno: { gap: espaco[1], padding: espaco[3], borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    valorPequeno: { ...fonte["numero-grande"], color: cor.texto },
    apoioPequeno: { ...fonte.rotulo, color: cor["texto-2"] },
    emDia: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: espaco[2], paddingHorizontal: espaco[3], borderRadius: raio.cartao, backgroundColor: cor["sucesso-suave"] },
    emDiaTexto: { ...fonte["corpo-forte"], color: cor.texto, flex: 1 },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
