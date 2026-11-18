// Aba "Treinos": todos os treinos, mais recente primeiro, rolagem infinita pelo cursor `proximo`. Filtros: modalidade e "Sem check-in".
// Cartão de atividade no formato proposto pela Lia (identidade v2): ícone e nome da modalidade, data e hora, fileira de números e selos de
// estado em ícone e palavra. Tokens atuais (a identidade v2 chega depois, com cantos mais discretos). Nada de saúde vai para log.
import { MaterialIcons } from "@expo/vector-icons";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from "react-native";

import { buscarTreinos, type ItemTreino, type ModalidadeFiltro } from "../treinos/api";
import { comFoco } from "../tema/foco";
import { EsqueletoPendentes } from "./Esqueleto";
import { dataCurta } from "./GraficoTiros";
import { MODALIDADES } from "./modalidades";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  apiUrl: string;
  atletaId: number;
  aoAbrirTreino: (atividadeId: number) => void;
  /** Abre já filtrada pelos treinos sem check-in (link "Check-ins pendentes" do Início). */
  semCheckinInicial?: boolean;
  /** Muda quando a aba volta ao foco: busca a primeira página de novo. */
  atualizar?: number;
  fetchFn?: typeof fetch;
  limite?: number;
};

type Estado = { tipo: "carregando" } | { tipo: "erro"; rede: boolean } | { tipo: "ok" };

const CHIPS: { valor: ModalidadeFiltro | null; texto: string }[] = [
  { valor: null, texto: "Todos" },
  { valor: "corrida", texto: "Corrida" },
  { valor: "natacao", texto: "Natação" },
  { valor: "ciclismo", texto: "Ciclismo" },
];

const TIPOS: Record<string, string> = { leve: "Leve", moderado: "Moderado", longo: "Longo", intervalado: "Intervalado", fartlek: "Fartlek" };

export const TEXTO_VAZIO = "Nenhum treino ainda";
export const TEXTO_VAZIO_FILTRO = "Nenhum treino com esses filtros.";
export const TEXTO_FIM = "Esses são todos os seus treinos.";

export function TelaTreinos({ apiUrl, atletaId, aoAbrirTreino, semCheckinInicial = false, atualizar = 0, fetchFn, limite = 20 }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const [modalidade, setModalidade] = useState<ModalidadeFiltro | null>(null);
  const [semCheckin, setSemCheckin] = useState(semCheckinInicial);
  const [itens, setItens] = useState<ItemTreino[]>([]);
  const [proximo, setProximo] = useState<string | null>(null);
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });
  const [maisCarregando, setMaisCarregando] = useState(false);
  const [maisErro, setMaisErro] = useState(false);
  const [tentativa, setTentativa] = useState(0);
  // Cada busca de primeira página invalida as respostas atrasadas das anteriores (troca de filtro).
  const geracao = useRef(0);
  const opcoes = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);

  // `semCheckinInicial` muda quando o link do Início leva à aba já filtrada.
  const [semCheckinDe, setSemCheckinDe] = useState(semCheckinInicial);
  if (semCheckinDe !== semCheckinInicial) {
    setSemCheckinDe(semCheckinInicial);
    setSemCheckin(semCheckinInicial);
  }

  useEffect(() => {
    const minha = ++geracao.current;
    buscarTreinos(atletaId, { limite, modalidade, checkinPendente: semCheckin }, opcoes).then((r) => {
      if (minha !== geracao.current) return;
      if (r.ok) {
        setItens(r.dados.itens);
        setProximo(r.dados.proximo ?? null);
        setMaisErro(false);
        setEstado({ tipo: "ok" });
      } else {
        // Um erro ao atualizar em segundo plano não apaga a lista que já está na tela.
        setEstado((atual) => (atual.tipo === "ok" ? atual : { tipo: "erro", rede: r.erro.tipo === "rede" }));
      }
    });
  }, [atletaId, limite, modalidade, semCheckin, opcoes, tentativa, atualizar]);

  const escolher = useCallback((m: ModalidadeFiltro | null) => {
    setModalidade(m);
    setItens([]);
    setProximo(null);
    setEstado({ tipo: "carregando" });
  }, []);
  const alternarSemCheckin = useCallback(() => {
    setSemCheckin((v) => !v);
    setItens([]);
    setProximo(null);
    setEstado({ tipo: "carregando" });
  }, []);
  const tentarDeNovo = useCallback(() => {
    setEstado({ tipo: "carregando" });
    setTentativa((n) => n + 1);
  }, []);

  const carregarMais = useCallback(async () => {
    if (!proximo || maisCarregando || estado.tipo !== "ok") return;
    const minha = geracao.current;
    setMaisCarregando(true);
    setMaisErro(false);
    const r = await buscarTreinos(atletaId, { limite, modalidade, checkinPendente: semCheckin, antesDe: proximo }, opcoes);
    if (minha !== geracao.current) return;
    setMaisCarregando(false);
    if (r.ok) {
      setItens((atual) => [...atual, ...r.dados.itens.filter((n) => !atual.some((a) => a.atividade_id === n.atividade_id))]);
      setProximo(r.dados.proximo ?? null);
    } else {
      setMaisErro(true);
    }
  }, [proximo, maisCarregando, estado.tipo, atletaId, limite, modalidade, semCheckin, opcoes]);

  const filtrado = modalidade !== null || semCheckin;

  const cabecalho = (
    <View style={styles.cabecalho}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Treinos
      </Text>
      <View accessibilityRole="radiogroup" style={styles.chips}>
        {CHIPS.map((c) => {
          const marcado = modalidade === c.valor;
          return (
            <Pressable
              key={c.texto}
              testID={`chip-${c.valor ?? "todos"}`}
              accessibilityRole="radio"
              accessibilityState={{ checked: marcado, selected: marcado }}
              onPress={() => escolher(c.valor)}
              style={comFoco([styles.chip, marcado && styles.chipMarcado], styles.foco)}
            >
              {marcado && <MaterialIcons name="check" size={tamanho.iconePequeno} color={tema.cor.destaque} accessible={false} />}
              <Text style={[styles.chipTexto, marcado && styles.chipTextoMarcado]}>{c.texto}</Text>
            </Pressable>
          );
        })}
        <Pressable
          testID="chip-sem-checkin"
          accessibilityRole="checkbox"
          accessibilityState={{ checked: semCheckin }}
          onPress={alternarSemCheckin}
          style={comFoco([styles.chip, semCheckin && styles.chipMarcado], styles.foco)}
        >
          <MaterialIcons name={semCheckin ? "check" : "assignment"} size={tamanho.iconePequeno} color={semCheckin ? tema.cor.destaque : tema.cor["texto-2"]} accessible={false} />
          <Text style={[styles.chipTexto, semCheckin && styles.chipTextoMarcado]}>Sem check-in</Text>
        </Pressable>
      </View>
    </View>
  );

  const rodape = (
    <View style={styles.rodape}>
      {estado.tipo === "ok" && maisCarregando && <ActivityIndicator testID="carregando-mais" color={tema.cor.destaque} />}
      {estado.tipo === "ok" && maisErro && (
        <View style={styles.maisErro}>
          <Text accessibilityRole="alert" style={styles.erro}>
            Não foi possível carregar mais treinos.
          </Text>
          <Pressable testID="tentar-mais" accessibilityRole="button" onPress={carregarMais} style={comFoco([styles.botao], styles.foco)}>
            <Text style={styles.botaoTexto}>Tentar de novo</Text>
          </Pressable>
        </View>
      )}
      {estado.tipo === "ok" && !proximo && itens.length > 0 && (
        <Text testID="fim-da-lista" style={styles.legenda}>
          {TEXTO_FIM}
        </Text>
      )}
    </View>
  );

  return (
    <FlatList
      testID="tela-treinos"
      data={estado.tipo === "ok" ? itens : []}
      keyExtractor={(i) => String(i.atividade_id)}
      renderItem={({ item }) => <CartaoTreino item={item} aoAbrir={() => aoAbrirTreino(item.atividade_id)} styles={styles} tema={tema} />}
      onEndReached={carregarMais}
      onEndReachedThreshold={0.5}
      contentContainerStyle={styles.container}
      ListHeaderComponent={cabecalho}
      ListEmptyComponent={
        <View>
          {estado.tipo === "carregando" && (
            <View>
              <Text accessibilityLiveRegion="polite" style={styles.texto}>
                Carregando seus treinos...
              </Text>
              <EsqueletoPendentes />
            </View>
          )}
          {estado.tipo === "erro" && (
            <View testID="estado-erro" style={styles.estado}>
              <MaterialIcons name={estado.rede ? "wifi-off" : "error-outline"} size={tamanho.iconeEstado} color={tema.cor.erro} accessible={false} />
              <Text accessibilityRole="alert" style={styles.erro}>
                {estado.rede ? "Não foi possível falar com o servidor" : "Não foi possível carregar os treinos. Tente de novo mais tarde."}
              </Text>
              <Pressable testID="tentar-de-novo" accessibilityRole="button" onPress={tentarDeNovo} style={comFoco([styles.botao], styles.foco)}>
                <Text style={styles.botaoTexto}>Tentar de novo</Text>
              </Pressable>
            </View>
          )}
          {estado.tipo === "ok" && (
            <View testID="estado-vazio" style={styles.estado}>
              <MaterialIcons name="fitness-center" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
              <Text accessibilityRole="header" style={styles.estadoTitulo}>
                {filtrado ? TEXTO_VAZIO_FILTRO : TEXTO_VAZIO}
              </Text>
            </View>
          )}
        </View>
      }
      ListFooterComponent={rodape}
    />
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function CartaoTreino({ item, aoAbrir, styles, tema }: { item: ItemTreino; aoAbrir: () => void; styles: Estilos; tema: Tema }) {
  const mod = MODALIDADES[item.modalidade];
  const nome = mod?.nome ?? "Treino";
  const quando = `${dataCurta(item.data_local)} às ${item.hora_local}`;
  const tipo = item.tipo_treino ? TIPOS[item.tipo_treino] : null;
  const selos: { chave: string; icone: React.ComponentProps<typeof MaterialIcons>["name"]; texto: string; atencao: boolean }[] = [];
  if (item.checkin_estado === "pendente") selos.push({ chave: "pendente", icone: "assignment", texto: "Check-in pendente", atencao: true });
  if (item.checkin_estado === "vencido") selos.push({ chave: "vencido", icone: "event-busy", texto: "Check-in vencido", atencao: false });
  if (item.feedback_estado === "pronto") selos.push({ chave: "pronto", icone: "check-circle-outline", texto: "Feedback pronto", atencao: false });
  if (item.feedback_estado === "desatualizado") selos.push({ chave: "desatualizado", icone: "update", texto: "Feedback desatualizado", atencao: true });
  const resumo = [nome, quando, tipo, item.duracao, item.distancia, ...selos.map((s) => s.texto)].filter(Boolean).join(", ");
  return (
    <Pressable
      testID={`treino-${item.atividade_id}`}
      accessibilityRole="button"
      accessibilityLabel={resumo}
      onPress={aoAbrir}
      style={comFoco(styles.cartao, styles.foco)}
    >
      <View style={styles.topo}>
        {mod && <MaterialIcons name={mod.icone} size={tamanho.iconeGrande} color={tema.cor[mod.cor]} accessible={false} />}
        <Text style={styles.nome}>{nome}</Text>
        {tipo && (
          <View style={styles.tipo}>
            <Text style={styles.tipoTexto}>{tipo}</Text>
          </View>
        )}
      </View>
      <Text style={styles.quando}>{quando}</Text>
      <View style={styles.numeros}>
        <Numero rotulo="Duração" valor={item.duracao} styles={styles} />
        {item.distancia ? <Numero rotulo="Distância" valor={item.distancia} styles={styles} /> : null}
      </View>
      {item.destaque ? (
        <Text testID={`destaque-${item.atividade_id}`} style={styles.destaque}>
          {item.destaque}
        </Text>
      ) : null}
      {selos.length > 0 && (
        <View style={styles.selos}>
          {selos.map((s) => (
            <View key={s.chave} testID={`selo-${s.chave}-${item.atividade_id}`} style={[styles.selo, s.atencao && styles.seloAtencao]}>
              <MaterialIcons name={s.icone} size={tamanho.iconePequeno} color={s.atencao ? tema.cor.alerta : tema.cor["texto-2"]} accessible={false} />
              <Text style={[styles.seloTexto, s.atencao && { color: tema.cor.alerta }]}>{s.texto}</Text>
            </View>
          ))}
        </View>
      )}
    </Pressable>
  );
}

function Numero({ rotulo, valor, styles }: { rotulo: string; valor: string; styles: Estilos }) {
  return (
    <View style={styles.numero}>
      <Text style={styles.numeroRotulo}>{rotulo}</Text>
      <Text style={styles.numeroValor}>{valor}</Text>
    </View>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    container: { padding: margem, alignSelf: "center", width: "100%", maxWidth: larguraConteudoMax + 2 * margem, flexGrow: 1 },
    cabecalho: { gap: espaco[3], marginBottom: espaco[3] },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    chips: { flexDirection: "row", flexWrap: "wrap", gap: espaco[2] },
    chip: { minHeight: tamanho.alvoMinimo, flexDirection: "row", alignItems: "center", gap: espaco[1], paddingHorizontal: espaco[3], borderRadius: raio.pilula, borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    chipMarcado: { backgroundColor: cor["destaque-suave"], borderColor: cor.destaque },
    chipTexto: { ...fonte.rotulo, color: cor.texto },
    chipTextoMarcado: { color: cor.destaque },
    // Cartão no formato proposto pela Lia: fileira de números; o raio é o token atual.
    cartao: { padding: espaco[4], gap: espaco[2], marginBottom: espaco[3], borderRadius: raio.grande, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    topo: { flexDirection: "row", alignItems: "center", gap: espaco[2] },
    nome: { ...fonte["titulo-secao"], color: cor.texto, flex: 1 },
    tipo: { paddingHorizontal: espaco[2], paddingVertical: 2, borderRadius: raio.pilula, backgroundColor: cor["superficie-2"] },
    tipoTexto: { ...fonte.legenda, color: cor.texto },
    quando: { ...fonte.rotulo, color: cor["texto-2"] },
    numeros: { flexDirection: "row", gap: espaco[5], marginTop: espaco[1] },
    numero: { gap: 2 },
    numeroRotulo: { ...fonte.legenda, color: cor["texto-2"] },
    numeroValor: { ...fonte["titulo-secao"], color: cor.texto, fontVariant: ["tabular-nums"] },
    destaque: { ...fonte.corpo, color: cor.texto },
    selos: { flexDirection: "row", flexWrap: "wrap", gap: espaco[2], marginTop: espaco[1] },
    selo: { flexDirection: "row", alignItems: "center", gap: espaco[1], paddingHorizontal: espaco[2], paddingVertical: 4, borderRadius: raio.pilula, backgroundColor: cor["superficie-2"] },
    seloAtencao: { backgroundColor: cor["alerta-suave"] },
    seloTexto: { ...fonte.legenda, color: cor["texto-2"] },
    estado: { alignItems: "center", paddingVertical: espaco[7], gap: espaco[2] },
    estadoTitulo: { ...fonte["titulo-secao"], color: cor.texto, textAlign: "center" },
    erro: { ...fonte.corpo, color: cor.erro, textAlign: "center" },
    botao: { minHeight: tamanho.botaoAltura, justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.medio, backgroundColor: cor.destaque },
    botaoTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    rodape: { paddingVertical: espaco[4], alignItems: "center" },
    maisErro: { alignItems: "center", gap: espaco[2] },
    legenda: { ...fonte.legenda, color: cor["texto-2"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
