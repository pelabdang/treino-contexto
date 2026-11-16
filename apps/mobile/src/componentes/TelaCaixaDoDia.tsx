// Caixa do dia do professor, lista de atenção (#426, spec docs/design/telas/caixa-do-dia.md, ADR 0015).
// O app só mostra o que a API manda: não calcula motivo, não ordena, não decide janela nem "novo".
// Privacidade: nada de aluno, PSE, sensação, atalho, observação ou feedback vai para log, URL, rota ou armazenamento;
// a observação só aparece dentro do detalhe aberto e nunca em rótulo de acessibilidade nem anúncio. O estado aberto fica só na memória.
import { MaterialIcons } from "@expo/vector-icons";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AccessibilityInfo, Platform, Pressable, ScrollView, type PressableStateCallbackType, StyleSheet, Text, View } from "react-native";

import { buscarCaixaDoDia, type AlunoCaixa, type CaixaDoDia, type DetalheTreino, type MotivoCaixa, type TreinoNovo } from "../caixa/api";
import { SENSACOES } from "../checkin/escala";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";
import { EsqueletoCaixa } from "./Esqueleto";
import { dataCurta } from "./GraficoTiros";
import { MODALIDADES } from "./modalidades";

type Props = {
  apiUrl: string;
  /** Professor do piloto (configuração). `null`: a tela mostra "não encontrada" sem chamar a API. */
  professorId: number | null;
  fetchFn?: typeof fetch;
};

type Falha = "rede" | "nao_encontrada" | "outro";
type Estado = { tipo: "carregando" } | { tipo: "ok"; dados: CaixaDoDia } | { tipo: "erro"; falha: Falha };

const ICONE_MOTIVO: Record<MotivoCaixa["codigo"], "healing" | "show-chart" | "event" | "schedule"> = {
  dor: "healing",
  fora_do_normal: "show-chart",
  divergencia: "event",
  checkin_vencendo: "schedule",
};
const DIAS = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"];
const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

/** "2025-11-13" -> "Quinta, 13/11/25" (só formatação da data local que a API mandou). */
export function dataDeHoje(hoje: string): string {
  const [a, m, d] = hoje.split("-").map(Number);
  if (!a || !m || !d) return hoje;
  return `${DIAS[new Date(Date.UTC(a, m - 1, d)).getUTCDay()]}, ${dataCurta(hoje)}`;
}
/** "2025-11-11" -> "11 de novembro" (para o leitor de tela). */
function dataPorExtenso(data: string): string {
  const [, m, d] = data.split("-").map(Number);
  return m && d ? `${d} de ${MESES[m - 1]}` : data;
}
/** Estilo de Pressable com fundo no hover (só a web manda `hovered`). */
const comHover = (base: object, hover: object) => (e: PressableStateCallbackType) => [base, (e as { hovered?: boolean }).hovered && hover];
const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;

export function TelaCaixaDoDia({ apiUrl, professorId, fetchFn }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const [estadoBusca, setEstado] = useState<Estado>({ tipo: "carregando" });
  const [atualizando, setAtualizando] = useState(false);
  const [falhaAoAtualizar, setFalhaAoAtualizar] = useState(false);
  const [abertos, setAbertos] = useState<ReadonlySet<string>>(new Set());
  const [tentativa, setTentativa] = useState(0);
  const manual = useRef(false);
  const temConteudo = useRef(false);
  // Sem professor configurado: o mesmo estado do 404, sem chamar a API.
  const estado: Estado = professorId === null ? { tipo: "erro", falha: "nao_encontrada" } : estadoBusca;

  const anunciar = useCallback((frase: string) => {
    if (Platform.OS === "android") return;
    try {
      AccessibilityInfo.announceForAccessibility?.(frase);
    } catch {
      // sem leitor de tela
    }
  }, []);

  useEffect(() => {
    if (professorId === null) return;
    let ativo = true;
    buscarCaixaDoDia(professorId, { baseUrl: apiUrl, fetch: fetchFn }).then((r) => {
      if (!ativo) return;
      const foiManual = manual.current;
      manual.current = false;
      setAtualizando(false);
      if (r.ok) {
        temConteudo.current = true;
        setFalhaAoAtualizar(false);
        setAbertos(new Set());
        setEstado({ tipo: "ok", dados: r.dados });
        if (foiManual) anunciar("Caixa do dia atualizada.");
      } else if (temConteudo.current) {
        // O conteúdo antigo fica; só um aviso no topo.
        setFalhaAoAtualizar(true);
      } else {
        setEstado({ tipo: "erro", falha: r.erro.tipo === "nao_encontrado" ? "nao_encontrada" : r.erro.tipo === "rede" ? "rede" : "outro" });
      }
    });
    return () => {
      ativo = false;
    };
  }, [apiUrl, professorId, fetchFn, tentativa, anunciar]);

  /** Botão "Atualizar" (o conteúdo continua na tela) e "Tentar de novo" (volta ao esqueleto). */
  const buscarDeNovo = useCallback(() => {
    if (temConteudo.current) {
      manual.current = true;
      setAtualizando(true);
      anunciar("Atualizando...");
    } else {
      setEstado({ tipo: "carregando" });
    }
    setTentativa((n) => n + 1);
  }, [anunciar]);

  const alternar = useCallback((chave: string) => {
    setAbertos((atual) => {
      const novo = new Set(atual);
      if (!novo.delete(chave)) novo.add(chave);
      return novo;
    });
  }, []);

  const dados = estado.tipo === "ok" ? estado.dados : null;
  const podeAtualizar = professorId !== null && estado.tipo !== "carregando" && !atualizando;

  return (
    <ScrollView testID="rolagem-tela" contentContainerStyle={styles.container}>
      <View style={styles.cabecalho}>
        <View style={styles.cabecalhoTextos}>
          <Text accessibilityRole="header" aria-level={1} style={styles.titulo}>
            Caixa do dia
          </Text>
          {dados && <Text style={styles.rotulo}>{dataDeHoje(dados.hoje)}</Text>}
        </View>
        {professorId !== null && (
          <Pressable
            testID="atualizar"
            accessibilityRole="button"
            accessibilityLabel="Atualizar a caixa do dia"
            accessibilityState={{ disabled: !podeAtualizar }}
            disabled={!podeAtualizar}
            onPress={buscarDeNovo}
            style={comHover(styles.atualizar, styles.hover)}
          >
            <MaterialIcons name="refresh" size={tamanho.iconeGrande} color={podeAtualizar ? tema.cor.destaque : tema.cor["texto-desligado"]} accessible={false} />
          </Pressable>
        )}
      </View>

      {estado.tipo === "carregando" && (
        <View>
          <Text accessibilityLiveRegion="polite" style={[styles.legenda, { marginTop: espaco[2] }]}>
            Carregando a caixa do dia...
          </Text>
          <EsqueletoCaixa />
        </View>
      )}

      {estado.tipo === "erro" && <EstadoDeErro falha={estado.falha} styles={styles} tema={tema} aoTentar={buscarDeNovo} />}

      {falhaAoAtualizar && (
        <Text testID="aviso-atualizar" accessibilityRole="alert" style={styles.aviso}>
          Não foi possível atualizar. Você está vendo a caixa de antes.
        </Text>
      )}

      {dados && dados.alunos.length === 0 && dados.novos.length === 0 && (
        <View testID="estado-sem-alunos" style={styles.estado}>
          <MaterialIcons name="group" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
          <Text accessibilityRole="header" style={styles.estadoTitulo}>
            Nenhum aluno na caixa do dia
          </Text>
          <Text style={styles.textoCentro}>Aparecem aqui os alunos com vínculo e consentimento registrados.</Text>
        </View>
      )}

      {dados && (dados.alunos.length > 0 || dados.novos.length > 0) && (
        <View>
          <Text testID="resumo" style={styles.resumo}>
            {`${plural(dados.alunos.filter((a) => !a.sem_motivo).length, "aluno para olhar", "alunos para olhar")} · ${plural(dados.novos.length, "treino novo", "treinos novos")}`}
          </Text>

          <View role="region" aria-label="Para olhar hoje" style={styles.secao}>
            <Text accessibilityRole="header" aria-level={2} style={styles.secaoTitulo}>
              Para olhar hoje
            </Text>
            <Text style={styles.legenda}>
              {`Últimos ${dados.janela_atencao_dias} dias. Primeiro quem tem dor marcada, depois fora do normal, diferença da semana-padrão e check-in perto do prazo.`}
            </Text>
            {dados.alunos.length > 0 && dados.alunos.every((a) => a.sem_motivo) && (
              <Text testID="nenhum-com-motivo" style={[styles.texto, { marginTop: espaco[3] }]}>
                {`Nenhum aluno com algo a destacar nos últimos ${dados.janela_atencao_dias} dias.`}
              </Text>
            )}
            {dados.alunos.map((aluno) =>
              aluno.sem_motivo ? (
                <View key={aluno.atleta_id} testID={`aluno-${aluno.atleta_id}`} style={styles.semMotivo}>
                  <Text accessibilityRole="header" aria-level={3} style={styles.corpoForte}>
                    {aluno.nome}
                  </Text>
                  <Text style={styles.texto}>{aluno.texto_sem_motivo ?? `Nada a destacar nos últimos ${dados.janela_atencao_dias} dias.`}</Text>
                </View>
              ) : (
                <CartaoAluno key={aluno.atleta_id} aluno={aluno} abertos={abertos} alternar={alternar} styles={styles} tema={tema} />
              ),
            )}
          </View>

          <View role="region" aria-label="Treinos novos" style={styles.secao}>
            <Text accessibilityRole="header" aria-level={2} style={styles.secaoTitulo}>
              Treinos novos
            </Text>
            <Text style={styles.legenda}>{`Últimos ${dados.janela_novos_dias} dias, com tipo sugerido.`}</Text>
            {dados.novos.length === 0 ? (
              <View testID="estado-sem-novos" style={styles.semNovos}>
                <MaterialIcons name="check-circle-outline" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
                <Text style={styles.texto}>Nenhum treino novo para confirmar.</Text>
              </View>
            ) : (
              dados.novos.map((n) => <LinhaNovo key={n.atividade_id} novo={n} aberto={abertos.has(`n-${n.atividade_id}`)} alternar={alternar} styles={styles} tema={tema} />)
            )}
          </View>
        </View>
      )}
    </ScrollView>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function EstadoDeErro({ falha, styles, tema, aoTentar }: { falha: Falha; styles: Estilos; tema: Tema; aoTentar: () => void }) {
  const naoEncontrada = falha === "nao_encontrada";
  return (
    <View testID="estado-erro" style={styles.estado}>
      <MaterialIcons name={falha === "rede" ? "wifi-off" : "error-outline"} size={tamanho.iconeEstado} color={naoEncontrada ? tema.cor["texto-2"] : tema.cor.erro} accessible={false} />
      <Text accessibilityRole="header" style={styles.estadoTitulo}>
        {naoEncontrada ? "Caixa do dia não encontrada" : falha === "rede" ? "Não foi possível falar com o servidor" : "Não foi possível carregar a caixa do dia. Tente de novo mais tarde."}
      </Text>
      {naoEncontrada && <Text style={styles.textoCentro}>Confira o professor configurado neste computador.</Text>}
      {falha === "rede" && <Text style={styles.textoCentro}>Sua caixa do dia continua como estava. Tente de novo.</Text>}
      {!naoEncontrada && (
        <Pressable accessibilityRole="button" onPress={aoTentar} style={styles.botao}>
          <Text style={styles.botaoTexto}>Tentar de novo</Text>
        </Pressable>
      )}
    </View>
  );
}

function CartaoAluno({ aluno, abertos, alternar, styles, tema }: { aluno: AlunoCaixa; abertos: ReadonlySet<string>; alternar: (c: string) => void; styles: Estilos; tema: Tema }) {
  return (
    <View testID={`aluno-${aluno.atleta_id}`} style={styles.cartao}>
      <Text accessibilityRole="header" aria-level={3} style={styles.secaoTitulo}>
        {aluno.nome}
      </Text>
      {aluno.treinos.map((t, i) => {
        const chave = `a-${t.atividade_id}`;
        const aberto = abertos.has(chave);
        const mod = MODALIDADES[t.modalidade];
        const resumo = `${mod?.nome ?? t.modalidade} · ${t.duracao_texto} · ${dataCurta(t.data_local)}`;
        const rotulo = `${t.motivos.map((m) => m.texto).join(" ")} ${mod?.nome ?? t.modalidade}, ${t.duracao_texto}, ${dataPorExtenso(t.data_local)}.`;
        return (
          <View key={t.atividade_id} style={i > 0 && styles.divisor}>
            <Pressable
              testID={`treino-${t.atividade_id}`}
              accessibilityRole="button"
              accessibilityLabel={rotulo}
              accessibilityState={{ expanded: aberto }}
              onPress={() => alternar(chave)}
              style={comHover(styles.linhaTreino, styles.hover)}
            >
              <View style={styles.linhaTextos}>
                <View style={styles.linhaModalidade}>
                  {mod && <MaterialIcons name={mod.icone} size={tamanho.iconeMedio} color={tema.cor[mod.cor]} accessible={false} />}
                  <Text style={styles.rotulo}>{resumo}</Text>
                </View>
                {t.motivos.map((m) => (
                  <View key={m.codigo} style={styles.motivo}>
                    <MaterialIcons name={ICONE_MOTIVO[m.codigo]} size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
                    <Text style={styles.motivoTexto}>{m.texto}</Text>
                  </View>
                ))}
              </View>
              <MaterialIcons name={aberto ? "expand-less" : "expand-more"} size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
            </Pressable>
            {aberto && <Detalhe detalhe={t.detalhe} testID={`detalhe-${t.atividade_id}`} styles={styles} tema={tema} />}
          </View>
        );
      })}
    </View>
  );
}

function LinhaNovo({ novo, aberto, alternar, styles, tema }: { novo: TreinoNovo; aberto: boolean; alternar: (c: string) => void; styles: Estilos; tema: Tema }) {
  const mod = MODALIDADES[novo.modalidade];
  const resumo = `${mod?.nome ?? novo.modalidade} · ${novo.duracao_texto} · ${dataCurta(novo.data_local)}`;
  const rotulo = `${novo.atleta_nome}, ${mod?.nome ?? novo.modalidade}, ${novo.duracao_texto}, ${dataPorExtenso(novo.data_local)}. Tipo sugerido ${novo.tipo_sugerido_texto}, ${novo.origem_texto}.`;
  return (
    <View testID={`novo-${novo.atividade_id}`} style={styles.cartao}>
      <Pressable
        testID={`treino-novo-${novo.atividade_id}`}
        accessibilityRole="button"
        accessibilityLabel={rotulo}
        accessibilityState={{ expanded: aberto }}
        onPress={() => alternar(`n-${novo.atividade_id}`)}
        style={comHover(styles.linhaTreino, styles.hover)}
      >
        <View style={styles.linhaTextos}>
          <Text style={styles.corpoForte}>{novo.atleta_nome}</Text>
          <View style={styles.linhaModalidade}>
            {mod && <MaterialIcons name={mod.icone} size={tamanho.iconeMedio} color={tema.cor[mod.cor]} accessible={false} />}
            <Text style={styles.rotulo}>{resumo}</Text>
          </View>
          <View style={styles.tipoLinha}>
            <View style={styles.chip}>
              <Text style={styles.chipTexto}>{novo.tipo_sugerido_texto}</Text>
            </View>
            <Text style={styles.legenda}>{`(${novo.origem_texto})`}</Text>
          </View>
        </View>
        <MaterialIcons name={aberto ? "expand-less" : "expand-more"} size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
      </Pressable>
      {aberto && <Detalhe detalhe={novo.detalhe} testID={`detalhe-novo-${novo.atividade_id}`} styles={styles} tema={tema} />}
    </View>
  );
}

function Detalhe({ detalhe, testID, styles, tema }: { detalhe: DetalheTreino; testID: string; styles: Estilos; tema: Tema }) {
  const c = detalhe.checkin;
  const sensacao = c ? SENSACOES.find((s) => s.valor === c.sensacao) : undefined;
  const f = detalhe.feedback;
  const feedback = f ? (f.estado === "pronto" && f.texto ? f.texto : f.mensagem) : null;
  const tipo = detalhe.tipo_texto ?? "Sem tipo";
  const linha = (rotulo: string, valor: string, extra?: string, icone?: (typeof SENSACOES)[number]["icone"]) => (
    <View style={styles.detalheLinha}>
      <Text style={styles.detalheRotulo}>{rotulo}</Text>
      <View style={styles.detalheValor}>
        <View style={styles.linhaModalidade}>
          {icone && <MaterialIcons name={icone} size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />}
          <Text style={styles.texto2}>{valor}</Text>
        </View>
        {extra ? <Text style={styles.legenda}>{extra}</Text> : null}
      </View>
    </View>
  );
  return (
    <View testID={testID} style={styles.detalhe}>
      {linha("Tipo", tipo, detalhe.tipo_origem_texto ?? undefined)}
      {c ? (
        <>
          {linha("Esforço", c.pse_texto)}
          {linha("Sensação", c.sensacao_texto, undefined, sensacao?.icone)}
          {linha("Atalhos", c.atalhos.length > 0 ? c.atalhos.map((a) => a.texto).join(", ") : c.nada_a_relatar ? "Nada a relatar" : "Nenhum")}
        </>
      ) : (
        <Text style={styles.texto}>Sem check-in ainda.</Text>
      )}
      {feedback ? linha("Feedback", feedback) : null}
      {c?.observacao ? (
        <View testID="observacao">
          <Text style={styles.detalheRotulo}>Observação do aluno</Text>
          <Text style={styles.legenda}>Só você vê. Não vai ao provedor de IA.</Text>
          <View style={styles.observacao}>
            <Text style={styles.texto2}>{c.observacao}</Text>
          </View>
        </View>
      ) : null}
    </View>
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
    cabecalho: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: espaco[3] },
    cabecalhoTextos: { flex: 1 },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    atualizar: { width: tamanho.alvoMinimo, height: tamanho.alvoMinimo, alignItems: "center", justifyContent: "center", borderRadius: raio.medio },
    hover: { backgroundColor: cor["superficie-2"] },
    rotulo: { ...fonte.rotulo, color: cor["texto-2"] },
    resumo: { ...fonte["corpo-forte"], color: cor.texto, marginTop: espaco[2] },
    secao: { marginTop: espaco[6] },
    secaoTitulo: { ...fonte["titulo-secao"], color: cor.texto },
    legenda: { ...fonte.legenda, color: cor["texto-2"] },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    texto2: { ...fonte.corpo, color: cor.texto, flexShrink: 1 },
    textoCentro: { ...fonte.corpo, color: cor["texto-2"], textAlign: "center" },
    corpoForte: { ...fonte["corpo-forte"], color: cor.texto },
    cartao: {
      marginTop: espaco[3],
      padding: espaco[4],
      gap: espaco[2],
      borderRadius: raio.grande,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    divisor: { borderTopWidth: borda.fina, borderTopColor: cor.borda, paddingTop: espaco[2] },
    linhaTreino: { minHeight: 72, flexDirection: "row", alignItems: "flex-start", gap: espaco[3], borderRadius: raio.medio },
    linhaTextos: { flex: 1, gap: espaco[1] },
    linhaModalidade: { flexDirection: "row", alignItems: "center", gap: espaco[2] },
    motivo: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2] },
    motivoTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    semMotivo: { paddingVertical: espaco[3], borderBottomWidth: borda.fina, borderBottomColor: cor.borda },
    semNovos: { flexDirection: "row", alignItems: "center", gap: espaco[2], marginTop: espaco[3] },
    tipoLinha: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: espaco[2] },
    chip: { paddingHorizontal: espaco[2], paddingVertical: espaco[1], borderRadius: raio.pilula, backgroundColor: cor["destaque-suave"] },
    chipTexto: { ...fonte.rotulo, color: cor.destaque },
    detalhe: { marginTop: espaco[2], padding: espaco[3], gap: espaco[2], borderRadius: raio.medio, backgroundColor: cor["superficie-2"] },
    detalheLinha: { flexDirection: "row", flexWrap: "wrap", gap: espaco[2] },
    detalheRotulo: { ...fonte.rotulo, color: cor["texto-2"], minWidth: 96 },
    detalheValor: { flex: 1, minWidth: 160 },
    observacao: { marginTop: espaco[1], paddingLeft: espaco[3], borderLeftWidth: 2, borderLeftColor: cor["borda-forte"] },
    aviso: { ...fonte.corpo, color: cor.erro, backgroundColor: cor["erro-suave"], padding: espaco[3], borderRadius: raio.medio, marginTop: espaco[3] },
    estado: { alignItems: "center", paddingVertical: espaco[7], gap: espaco[2] },
    estadoTitulo: { ...fonte["titulo-secao"], color: cor.texto, textAlign: "center" },
    botao: { minHeight: tamanho.botaoAltura, justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.medio, backgroundColor: cor.destaque, marginTop: espaco[3] },
    botaoTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
  });
}
