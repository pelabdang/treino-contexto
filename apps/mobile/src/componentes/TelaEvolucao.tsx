import {
  buscarCatalogoSeries,
  buscarSerieEvolucao,
  type CatalogoSeries,
  type ErroApi,
  type PeriodoSerie,
  type SerieEvolucao,
} from "@treino/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { MaterialIcons } from "@expo/vector-icons";
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import { buscarCheckinsPendentes } from "../checkin/api";
import { buscarProfessores, totalAguardando } from "../consentimento/api";
import { BotaoEnviarFit } from "./BotaoEnviarFit";
import { EsqueletoEvolucao } from "./Esqueleto";
import {
  borda,
  espaco,
  familia,
  fonte,
  larguraConteudoMax,
  larguraMargemGrande,
  raio,
  tamanho,
  useMargemTela,
  useTema,
  type Tema,
} from "../tema";
import { gravarUltimaSerie, lerUltimaSerie } from "../sessao/armazenamento";
import { GraficoSerie } from "./GraficoSerie";
import { SeletorSerie } from "./SeletorSerie";

type Props = {
  apiUrl: string;
  atletaId: number;
  /** Abre a tela do treino. Sem ele, o botão "Ver treino" não aparece. */
  aoAbrirTreino?: (atividadeId: number) => void;
  /** Abre a tela da semana-padrão. Sem ele, o botão "Semana-padrão" não aparece. */
  aoAbrirSemanaPadrao?: () => void;
  /** Abre a lista de check-ins pendentes (#299). Sem ele, a linha "Check-ins pendentes" não aparece nem busca o total. */
  aoAbrirCheckinsPendentes?: () => void;
  /** Abre a lista de consentimentos (#503). Sem ele, não busca nem mostra o aviso de pedido de professor. */
  aoAbrirConsentimento?: () => void;
  /** Esconde "Enviar arquivo FIT" (agora na aba Conta). No estado vazio o botão volta, porque o texto o cita. */
  ocultarEnviarFit?: boolean;
  /** Muda quando a tela volta ao foco: busca o total de pendentes de novo. */
  atualizar?: number;
  /** Troque nos testes. Padrão: o fetch global. */
  fetchFn?: typeof fetch;
};

type EstadoCatalogo = { tipo: "carregando" } | { tipo: "ok"; dados: CatalogoSeries } | { tipo: "erro"; erro: ErroApi };
type EstadoSerie = { tipo: "carregando" } | { tipo: "ok"; dados: SerieEvolucao } | { tipo: "erro"; erro: ErroApi };

const PERIODOS: { id: PeriodoSerie; texto: string }[] = [
  { id: "12s", texto: "12 semanas" },
  { id: "6m", texto: "6 meses" },
  { id: "1a", texto: "1 ano" },
];

function mensagemErro(erro: ErroApi): string {
  return erro.tipo === "nao_encontrado" ? "Atleta não encontrado" : "Não foi possível carregar esta série.";
}

export function TelaEvolucao({
  apiUrl,
  atletaId,
  aoAbrirTreino,
  aoAbrirSemanaPadrao,
  aoAbrirCheckinsPendentes,
  aoAbrirConsentimento,
  ocultarEnviarFit = false,
  atualizar = 0,
  fetchFn,
}: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const [catalogo, setCatalogo] = useState<EstadoCatalogo>({ tipo: "carregando" });
  const [serie, setSerie] = useState<EstadoSerie>({ tipo: "carregando" });
  const [tentativa, setTentativa] = useState(0);
  const [escolhidaId, setEscolhidaId] = useState<string | null>(null);
  const [periodo, setPeriodo] = useState<PeriodoSerie>("12s");
  const [selecionado, setSelecionado] = useState<number | null>(null);
  const [lista, setLista] = useState(false);
  const [abrirFolha, setAbrirFolha] = useState(0);
  const larga = useWindowDimensions().width >= larguraMargemGrande;

  // 1) Catálogo. A série inicial: a última que o atleta escolheu (guardada no aparelho); na primeira vez, a `serie_padrao`.
  useEffect(() => {
    let ativo = true;
    (async () => {
      const [r, guardada] = await Promise.all([
        buscarCatalogoSeries(atletaId, { baseUrl: apiUrl, fetch: fetchFn }),
        lerUltimaSerie(atletaId),
      ]);
      if (!ativo) return;
      if (!r.ok) return setCatalogo({ tipo: "erro", erro: r.erro });
      setCatalogo({ tipo: "ok", dados: r.dados });
      setEscolhidaId((atual) => {
        if (atual && r.dados.series.some((s) => s.id === atual)) return atual;
        const lembrada = r.dados.series.find((s) => s.id === guardada && s.disponivel);
        return lembrada?.id ?? r.dados.serie_padrao ?? r.dados.series.find((s) => s.disponivel)?.id ?? r.dados.series[0]?.id ?? null;
      });
    })();
    return () => {
      ativo = false;
    };
  }, [apiUrl, atletaId, fetchFn, tentativa]);

  // 2) A série escolhida, no período escolhido.
  const catalogoOk = catalogo.tipo === "ok" ? catalogo.dados : null;
  const entrada = catalogoOk?.series.find((x) => x.id === escolhidaId);
  const buscaSerie = entrada?.disponivel ? escolhidaId : null;
  useEffect(() => {
    if (!buscaSerie) return;
    let ativo = true;
    buscarSerieEvolucao(atletaId, buscaSerie, periodo, { baseUrl: apiUrl, fetch: fetchFn }).then((r) => {
      if (!ativo) return;
      setSelecionado(null);
      setSerie(r.ok ? { tipo: "ok", dados: r.dados } : { tipo: "erro", erro: r.erro });
    });
    return () => {
      ativo = false;
    };
  }, [apiUrl, atletaId, fetchFn, buscaSerie, periodo, tentativa]);

  const escolher = useCallback(
    (id: string) => {
      if (id === escolhidaId) return;
      setSerie({ tipo: "carregando" });
      setEscolhidaId(id);
      setSelecionado(null);
      void gravarUltimaSerie(atletaId, id);
    },
    [atletaId, escolhidaId],
  );
  const mudarPeriodo = useCallback(
    (p: PeriodoSerie) => {
      if (p === periodo) return;
      setSerie({ tipo: "carregando" });
      setPeriodo(p);
    },
    [periodo],
  );

  // Total de treinos sem check-in (uma chamada a mais ao abrir). Se falhar, a linha aparece sem número.
  const [pendentes, setPendentes] = useState<number | null>(null);
  const querPendentes = !!aoAbrirCheckinsPendentes;
  useEffect(() => {
    if (!querPendentes) return;
    let ativo = true;
    buscarCheckinsPendentes(atletaId, undefined, { baseUrl: apiUrl, fetch: fetchFn }).then((r) => {
      if (ativo) setPendentes(r.ok && typeof r.dados.total === "number" ? r.dados.total : null);
    });
    return () => {
      ativo = false;
    };
  }, [querPendentes, apiUrl, atletaId, fetchFn, atualizar]);

  // Pedido de professor aguardando resposta (#503): uma chamada a mais; se falhar ou não vier lista, o aviso não aparece.
  const [pedidos, setPedidos] = useState(0);
  const querPedidos = !!aoAbrirConsentimento;
  useEffect(() => {
    if (!querPedidos) return;
    let ativo = true;
    buscarProfessores(atletaId, { baseUrl: apiUrl, fetch: fetchFn }).then((r) => {
      if (ativo) setPedidos(r.ok && Array.isArray(r.dados.professores) ? totalAguardando(r.dados.professores) : 0);
    });
    return () => {
      ativo = false;
    };
  }, [querPedidos, apiUrl, atletaId, fetchFn, atualizar]);

  const tentarDeNovo = useCallback(() => {
    setCatalogo((c) => (c.tipo === "erro" ? { tipo: "carregando" } : c));
    setSerie({ tipo: "carregando" });
    setTentativa((n) => n + 1);
  }, []);

  // Depois de um envio com sucesso, busca a evolução de novo (sem esconder o que já está na tela).
  const recarregar = useCallback(() => setTentativa((n) => n + 1), []);

  const semNenhuma = catalogoOk !== null && !catalogoOk.series.some((x) => x.disponivel);
  const vazio = semNenhuma;

  return (
    <ScrollView testID="rolagem-tela" contentContainerStyle={styles.container}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Evolução
      </Text>
      {aoAbrirConsentimento && pedidos > 0 && (
        <View testID="aviso-consentimento" accessibilityLiveRegion="polite" style={styles.avisoPedido}>
          <MaterialIcons name="info-outline" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
          <Text style={styles.avisoPedidoTexto}>Há um professor pedindo para ver seus treinos.</Text>
          <Pressable testID="ver-pedido" accessibilityRole="button" accessibilityLabel="Ver o pedido do professor" onPress={aoAbrirConsentimento} style={styles.avisoPedidoBotao}>
            <Text style={styles.verTreinoTexto}>Ver</Text>
          </Pressable>
        </View>
      )}
      {aoAbrirSemanaPadrao && (
        <Pressable
          testID="abrir-semana-padrao"
          accessibilityRole="button"
          accessibilityLabel="Semana-padrão"
          onPress={aoAbrirSemanaPadrao}
          style={({ pressed }) => [styles.verTreino, styles.semanaPadrao, pressed && { backgroundColor: tema.cor["marca-suave"] }]}
        >
          <MaterialIcons name="event" size={tamanho.iconeMedio} color={tema.cor.link} accessible={false} />
          <Text style={styles.verTreinoTexto}>Semana-padrão</Text>
          <MaterialIcons name="chevron-right" size={tamanho.iconeMedio} color={tema.cor.link} accessible={false} />
        </Pressable>
      )}
      {aoAbrirCheckinsPendentes && (
        <Pressable
          testID="abrir-checkins-pendentes"
          accessibilityRole="button"
          accessibilityLabel={pendentes ? `Check-ins pendentes, ${pendentes}` : "Check-ins pendentes"}
          onPress={aoAbrirCheckinsPendentes}
          style={({ pressed }) => [styles.verTreino, styles.semanaPadrao, pressed && { backgroundColor: tema.cor["marca-suave"] }]}
        >
          <MaterialIcons name="assignment" size={tamanho.iconeMedio} color={tema.cor.link} accessible={false} />
          <Text style={styles.verTreinoTexto}>Check-ins pendentes{pendentes ? ` · ${pendentes}` : ""}</Text>
          <MaterialIcons name="chevron-right" size={tamanho.iconeMedio} color={tema.cor.link} accessible={false} />
        </Pressable>
      )}
      {(!ocultarEnviarFit || vazio) && (
        <BotaoEnviarFit
          apiUrl={apiUrl}
          atletaId={atletaId}
          fetchFn={fetchFn}
          aoEnviar={recarregar}
          variante={vazio ? "primario" : "secundario"}
        />
      )}
      {catalogo.tipo === "carregando" && (
        <View>
          <Text accessibilityLiveRegion="polite" style={styles.texto}>
            Carregando...
          </Text>
          <EsqueletoEvolucao />
        </View>
      )}
      {catalogo.tipo === "erro" && <Erro erro={catalogo.erro} aoTentar={tentarDeNovo} styles={styles} tema={tema} />}
      {catalogoOk && semNenhuma && (
        <View testID="estado-vazio" style={styles.estado}>
          <MaterialIcons name="insert-chart-outlined" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
          <Text accessibilityRole="header" style={styles.estadoTitulo}>
            Ainda não há evolução para mostrar
          </Text>
          <Text style={styles.texto}>Envie o arquivo do seu relógio pela aba Conta e a evolução aparece aqui.</Text>
        </View>
      )}
      {catalogoOk && !semNenhuma && escolhidaId && (
        <View style={larga ? styles.duasColunas : undefined}>
          <View style={larga ? styles.colunaEsq : undefined}>
            <Text style={styles.subtitulo}>Escolha o que acompanhar</Text>
            <SeletorSerie series={catalogoOk.series} escolhida={escolhidaId} aoEscolher={(x) => escolher(x.id)} larga={larga} abrirFolha={abrirFolha} />
          </View>
          <View style={larga ? styles.colunaDir : undefined}>
            {entrada && !entrada.disponivel && (
              <View testID="serie-indisponivel" style={styles.estado}>
                <MaterialIcons name="insert-chart-outlined" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
                <Text accessibilityRole="header" style={styles.estadoTitulo}>
                  {entrada.titulo}
                </Text>
                <Text style={styles.texto}>{entrada.motivo}</Text>
                <EscolherOutra styles={styles} aoPressionar={() => setAbrirFolha((n) => n + 1)} visivel={!larga} />
              </View>
            )}
            {entrada?.disponivel && serie.tipo === "carregando" && (
              <View>
                <Text accessibilityLiveRegion="polite" style={styles.apenasLeitor}>
                  Carregando
                </Text>
                <EsqueletoEvolucao />
              </View>
            )}
            {entrada?.disponivel && serie.tipo === "erro" && <Erro erro={serie.erro} aoTentar={tentarDeNovo} styles={styles} tema={tema} />}
            {entrada?.disponivel && serie.tipo === "ok" && (
              <SerieOk
                dados={serie.dados}
                periodo={periodo}
                aoMudarPeriodo={mudarPeriodo}
                selecionado={selecionado}
                aoSelecionar={setSelecionado}
                lista={lista}
                aoAlternarLista={() => setLista((v) => !v)}
                aoAbrirTreino={aoAbrirTreino}
                aoEscolherOutra={() => setAbrirFolha((n) => n + 1)}
                larga={larga}
                styles={styles}
                tema={tema}
              />
            )}
          </View>
        </View>
      )}
    </ScrollView>
  );
}

function Erro({ erro, aoTentar, styles, tema }: { erro: ErroApi; aoTentar: () => void; styles: Estilos; tema: Tema }) {
  return (
    <View testID="estado-erro" style={styles.estado}>
      <MaterialIcons name={erro.tipo === "rede" ? "wifi-off" : "error-outline"} size={tamanho.iconeEstado} color={tema.cor.erro} accessible={false} />
      <Text accessibilityRole="alert" style={styles.erro}>
        {mensagemErro(erro)}
      </Text>
      {erro.tipo !== "nao_encontrado" && (
        <>
          <Text style={styles.texto}>Verifique a conexão e tente de novo.</Text>
          <Pressable
            accessibilityRole="button"
            onPress={aoTentar}
            style={({ pressed }) => [styles.botao, pressed && { backgroundColor: tema.cor["botao-pressionado"] }]}
          >
            <Text style={styles.botaoTexto}>Tentar de novo</Text>
          </Pressable>
        </>
      )}
    </View>
  );
}

function EscolherOutra({ styles, aoPressionar, visivel }: { styles: Estilos; aoPressionar: () => void; visivel: boolean }) {
  if (!visivel) return null;
  return (
    <Pressable testID="escolher-outra" accessibilityRole="button" onPress={aoPressionar} style={styles.verTreino}>
      <Text style={styles.verTreinoTexto}>Escolher outra série</Text>
    </Pressable>
  );
}

function SerieOk({
  dados,
  periodo,
  aoMudarPeriodo,
  selecionado,
  aoSelecionar,
  lista,
  aoAlternarLista,
  aoAbrirTreino,
  aoEscolherOutra,
  larga,
  styles,
  tema,
}: {
  dados: SerieEvolucao;
  periodo: PeriodoSerie;
  aoMudarPeriodo: (p: PeriodoSerie) => void;
  selecionado: number | null;
  aoSelecionar: (i: number | null) => void;
  lista: boolean;
  aoAlternarLista: () => void;
  aoAbrirTreino?: (atividadeId: number) => void;
  aoEscolherOutra: () => void;
  larga: boolean;
  styles: Estilos;
  tema: Tema;
}) {
  const pontos = dados.pontos;
  if (pontos.length === 0) {
    return (
      <View testID="estado-vazio" style={styles.estado}>
        <MaterialIcons name="insert-chart-outlined" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
        <Text accessibilityRole="header" style={styles.estadoTitulo}>
          {dados.titulo}
        </Text>
        <Text style={styles.texto}>{dados.frase.texto}</Text>
        <EscolherOutra styles={styles} aoPressionar={aoEscolherOutra} visivel />
      </View>
    );
  }
  const ponto = selecionado != null ? pontos[selecionado] : null;
  const vizinho = (passo: number) => {
    if (selecionado == null) return null;
    for (let i = selecionado + passo; i >= 0 && i < pontos.length; i += passo) if (pontos[i].valor != null) return i;
    return null;
  };
  const anterior = vizinho(-1);
  const seguinte = vizinho(1);
  const selo = (p: (typeof pontos)[number]) =>
    p.normal_estado === "fora" ? "fora do seu normal" : p.normal_estado === "dentro" ? "dentro do seu normal" : p.normal_estado === "aprendendo" ? "normal em aprendizado" : null;
  return (
    <View>
      <View testID="frase-evolucao" style={styles.frase}>
        <Text style={styles.sobretitulo}>EM UMA FRASE</Text>
        <Text style={styles.fraseTexto}>{dados.frase.texto}</Text>
      </View>
      <View style={styles.cartao}>
        {dados.ultimo_valor_texto != null && (
          <View accessible accessibilityLabel={`${dados.ultimo_valor_texto} ${dados.unidade}, ${dados.ultimo_rotulo ?? ""}`}>
            <View style={styles.valorLinhaGrande}>
              <Text style={styles.numeroGrande}>{dados.ultimo_valor_texto}</Text>
              <Text style={styles.unidade}>{dados.unidade}</Text>
            </View>
            {dados.ultimo_rotulo && <Text style={styles.rotulo}>{dados.ultimo_rotulo}</Text>}
          </View>
        )}
        <GraficoSerie serie={dados} selecionado={selecionado} aoSelecionar={aoSelecionar} />
        {dados.aprendendo_texto && (
          <Text testID="aprendendo" style={styles.aviso}>
            {dados.aprendendo_texto}
          </Text>
        )}
        <View accessibilityRole="tablist" style={styles.periodos}>
          {PERIODOS.map((p) => (
            <Pressable
              key={p.id}
              testID={`periodo-${p.id}`}
              accessibilityRole="tab"
              accessibilityState={{ selected: p.id === periodo }}
              onPress={() => aoMudarPeriodo(p.id)}
              style={[styles.periodo, p.id === periodo && styles.periodoAtivo]}
            >
              <Text style={[styles.periodoTexto, p.id === periodo && styles.periodoTextoAtivo]}>{p.texto}</Text>
            </Pressable>
          ))}
        </View>
        {ponto ? (
          <View testID="detalhe-ponto" style={styles.detalhe}>
            <Text style={styles.detalheTitulo}>{ponto.data_texto}</Text>
            <View style={styles.valorLinhaGrande}>
              <Text style={styles.detalheValor}>{ponto.valor_texto ?? "sem valor"}</Text>
              {ponto.valor_texto != null && <Text style={styles.unidade}>{dados.unidade}</Text>}
            </View>
            {selo(ponto) && <Text style={styles.rotulo}>{selo(ponto)}</Text>}
            <Text style={styles.legenda}>{ponto.rotulo}</Text>
            {aoAbrirTreino && ponto.atividade_id != null && (
              <Pressable
                testID="abrir-treino"
                accessibilityRole="button"
                onPress={() => aoAbrirTreino(ponto.atividade_id as number)}
                style={({ pressed }) => [styles.botao, pressed && { backgroundColor: tema.cor["botao-pressionado"] }]}
              >
                <Text style={styles.botaoTexto}>Abrir treino</Text>
              </Pressable>
            )}
            <View style={styles.setas}>
              <Pressable
                testID="treino-anterior"
                accessibilityRole="button"
                accessibilityState={{ disabled: anterior == null }}
                disabled={anterior == null}
                onPress={() => anterior != null && aoSelecionar(anterior)}
                style={[styles.seta, anterior == null && styles.setaOff]}
              >
                <Text style={styles.verTreinoTexto}>{dados.id.includes("volume") ? "Semana anterior" : "Treino anterior"}</Text>
              </Pressable>
              <Pressable
                testID="treino-seguinte"
                accessibilityRole="button"
                accessibilityState={{ disabled: seguinte == null }}
                disabled={seguinte == null}
                onPress={() => seguinte != null && aoSelecionar(seguinte)}
                style={[styles.seta, seguinte == null && styles.setaOff]}
              >
                <Text style={styles.verTreinoTexto}>{dados.id.includes("volume") ? "Semana seguinte" : "Treino seguinte"}</Text>
              </Pressable>
            </View>
          </View>
        ) : (
          <Text style={styles.legenda}>
            {pontos.length} {pontos.length === 1 ? "ponto" : "pontos"} no período. Toque num ponto para ver os detalhes.
          </Text>
        )}
        <Pressable
          testID="ver-lista"
          accessibilityRole="button"
          accessibilityState={{ expanded: lista }}
          onPress={aoAlternarLista}
          style={styles.verTreino}
        >
          <Text style={styles.verTreinoTexto}>{lista ? "Esconder a lista" : "Ver os valores em lista"}</Text>
        </Pressable>
        {lista && (
          <View testID="lista-pontos" accessibilityRole="list">
            {[...pontos.keys()].reverse().map((i) => (
              <Pressable
                key={i}
                testID={`linha-ponto-${i}`}
                accessibilityRole="button"
                accessibilityState={{ selected: i === selecionado }}
                accessibilityLabel={pontos[i].rotulo}
                onPress={() => aoSelecionar(i)}
                style={[styles.linhaPonto, i === selecionado && { backgroundColor: tema.cor["marca-suave"] }]}
              >
                <Text style={styles.celula}>{pontos[i].data_texto}</Text>
                <Text style={styles.celula}>{pontos[i].valor_texto ?? "sem valor"}</Text>
              </Pressable>
            ))}
          </View>
        )}
      </View>
      <View style={styles.rodape}>
        <Text style={styles.pequeno}>cálculo: {dados.versao_calculo}</Text>
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
      borderRadius: raio.botao,
      backgroundColor: cor.botao,
    },
    botaoTexto: { ...fonte.botao, color: cor["sobre-botao"] },
    verTreino: {
      flexDirection: "row",
      alignItems: "center",
      alignSelf: "flex-start",
      minHeight: tamanho.botaoAltura,
      paddingRight: espaco[2],
      borderRadius: raio.botao,
    },
    verTreinoTexto: { ...fonte.botao, color: cor.link },
    semanaPadrao: { gap: espaco[2], marginBottom: espaco[2] },
    avisoPedido: { flexDirection: "row", alignItems: "center", gap: espaco[2], marginBottom: espaco[2], paddingLeft: espaco[3], borderRadius: raio.bloco, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor["superficie-2"] },
    avisoPedidoTexto: { ...fonte.corpo, flex: 1, color: cor.texto, paddingVertical: espaco[2] },
    avisoPedidoBotao: { minHeight: tamanho.botaoAltura, minWidth: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", paddingHorizontal: espaco[3] },
    cartao: {
      marginTop: espaco[4],
      padding: espaco[4],
      borderRadius: raio.cartao,
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
    subtitulo: { ...fonte.rotulo, color: cor["texto-2"], marginBottom: espaco[2] },
    duasColunas: { flexDirection: "row", gap: espaco[5], alignItems: "flex-start" },
    colunaEsq: { width: 300 },
    colunaDir: { flex: 1 },
    apenasLeitor: { position: "absolute", width: 1, height: 1, opacity: 0 },
    frase: { marginTop: espaco[4], padding: espaco[3], borderRadius: raio.bloco, backgroundColor: cor["marca-suave"] },
    sobretitulo: { ...fonte.sobretitulo, color: cor["texto-2"], marginBottom: espaco[1] },
    fraseTexto: { fontFamily: familia.regular, fontSize: 14.5, lineHeight: 21, color: cor.texto },
    valorLinhaGrande: { flexDirection: "row", alignItems: "baseline", gap: espaco[1] },
    numeroGrande: { ...fonte["numero-grande"], fontSize: 44, lineHeight: 48, color: cor.texto },
    aviso: { ...fonte.rotulo, color: cor["texto-2"], marginTop: espaco[2] },
    periodos: { flexDirection: "row", gap: espaco[2], flexWrap: "wrap", marginTop: espaco[3] },
    periodo: { minHeight: tamanho.alvoMinimo, justifyContent: "center", paddingHorizontal: espaco[3], borderRadius: raio.botao, borderWidth: borda.fina, borderColor: cor.borda },
    periodoAtivo: { backgroundColor: cor["marca-suave"], borderColor: cor.link },
    periodoTexto: { ...fonte.rotulo, color: cor.texto },
    periodoTextoAtivo: { color: cor.link },
    detalhe: { marginTop: espaco[3], padding: espaco[3], borderLeftWidth: 4, borderLeftColor: cor["grafico.pace"], backgroundColor: cor["superficie-2"], borderRadius: raio.bloco, gap: espaco[1] },
    detalheTitulo: { ...fonte["titulo-cartao"], color: cor.texto },
    detalheValor: { ...fonte["numero-destaque"], color: cor.texto },
    legenda: { ...fonte.legenda, color: cor["texto-2"], marginTop: espaco[2] },
    setas: { flexDirection: "row", flexWrap: "wrap", gap: espaco[2], marginTop: espaco[1] },
    seta: { minHeight: tamanho.alvoMinimo, justifyContent: "center", paddingRight: espaco[2] },
    setaOff: { opacity: 0.4 },
    linhaPonto: { minHeight: tamanho.alvoMinimo, flexDirection: "row", alignItems: "center", gap: espaco[3], paddingHorizontal: espaco[2], borderBottomWidth: borda.fina, borderBottomColor: cor.borda },
    pequeno: { ...fonte.legenda, color: cor["texto-2"] },
  });
}
