// Caixa do dia do professor, lista de atenção (#426, spec docs/design/telas/caixa-do-dia.md, ADR 0015).
// O app só mostra o que a API manda: não calcula motivo, não ordena, não decide janela nem "novo".
// Privacidade: nada de aluno, PSE, sensação, atalho, observação ou feedback vai para log, URL, rota ou armazenamento;
// a observação só aparece dentro do detalhe aberto e nunca em rótulo de acessibilidade nem anúncio. O estado aberto fica só na memória.
import { MaterialIcons } from "@expo/vector-icons";
import { useCallback, type ComponentRef, useEffect, useMemo, useRef, useState } from "react";
import { AccessibilityInfo, ActivityIndicator, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import {
  buscarCaixaDoDia,
  codigoDoErro,
  confirmarTiposDeTreino,
  TIPOS,
  type AlunoCaixa,
  type CaixaDoDia,
  type DetalheTreino,
  type MotivoCaixa,
  type TipoTreino,
  type TiposConfirmados,
  type TreinoNovo,
} from "../caixa/api";
import { SENSACOES } from "../checkin/escala";
import { FOCAVEL, focar, rolarAte } from "../navegacao/foco";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";
import { BarraLote, type ErroLote } from "./BarraLote";
import { EsqueletoCaixa } from "./Esqueleto";
import { FolhaTipo } from "./FolhaTipo";
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
const comHover = (base: object, hover: object, foco: object) => comFoco(base, foco, hover);
/** A linha de treino tem alvo de toque de 72 sem crescer o cartão: a área extra é só de toque. */
const ALVO_LINHA = { top: 16, bottom: 16 };
/** Máximo de itens do `PUT` em lote (#425). */
const LIMITE_LOTE = 200;
const textoDoTipo = (t: TipoTreino) => TIPOS.find((x) => x.valor === t)?.texto ?? t;
/** "3 treinos salvos: 2 confirmados e 1 corrigido." (os números vêm da resposta do `PUT`). */
export function textoSalvo({ confirmados: c, corrigidos: k }: TiposConfirmados): string {
  const t = c + k;
  return `${t} ${t === 1 ? "treino salvo" : "treinos salvos"}: ${c} ${c === 1 ? "confirmado" : "confirmados"} e ${k} ${k === 1 ? "corrigido" : "corrigidos"}.`;
}
const TEXTO_ERRO_LOTE = {
  servidor: "Não foi possível falar com o servidor. Nada foi salvo. Tente de novo.",
  indisponivel: "Algum treino não está mais disponível para você. Nada foi salvo. Atualize a lista e escolha de novo.",
  semTipo: "Algum treino não aceita tipo. Nada foi salvo. Atualize a lista.",
  validacao: "Algum dado do lote não foi aceito. Nada foi salvo. Tente de novo mais tarde.",
};
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
  // Lote (#427): só na memória. `null` = confirmar o tipo sugerido; um tipo = corrigir para ele.
  const [selecao, setSelecao] = useState<ReadonlyMap<number, TipoTreino | null>>(new Map());
  const [salvando, setSalvando] = useState(false);
  const [erroLote, setErroLote] = useState<ErroLote | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);
  const [folha, setFolha] = useState<number | null>(null);
  const [anuncio, setAnuncio] = useState("");
  const rolagem = useRef<ComponentRef<typeof ScrollView>>(null);
  const tituloNovos = useRef<ComponentRef<typeof Text>>(null);
  const linhasNovas = useRef(new Map<number, ComponentRef<typeof View> | null>());
  const origemFolha = useRef<unknown>(null);
  const manual = useRef(false);
  const temConteudo = useRef(false);
  // Sem professor configurado: o mesmo estado do 404, sem chamar a API.
  const estado: Estado = professorId === null ? { tipo: "erro", falha: "nao_encontrada" } : estadoBusca;

  // Android: região viva sempre montada (muda o texto, o leitor lê). iOS e web: `announceForAccessibility`. Só texto, sem dado de saúde.
  const anunciar = useCallback((frase: string) => {
    setAnuncio((a) => (a === frase ? `${frase}\u200B` : frase));
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
        // Quem já saiu da lista (salvo, ou fora da janela) sai da seleção.
        const ids = new Set(r.dados.novos.map((n) => n.atividade_id));
        setSelecao((atual) => new Map([...atual].filter(([id]) => ids.has(id))));
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

  // Depois de salvar, as linhas onde estava o foco saíram: o foco vai ao título "Treinos novos" (e o leitor de tela o lê).
  useEffect(() => {
    if (sucesso) focar(tituloNovos.current);
  }, [sucesso]);

  const dados = estado.tipo === "ok" ? estado.dados : null;
  const podeAtualizar = professorId !== null && estado.tipo !== "carregando" && !atualizando && !salvando;

  const marcar = useCallback((id: number) => {
    setSucesso(null);
    setErroLote(null);
    setSelecao((atual) => {
      const novo = new Map(atual);
      if (!novo.delete(id)) novo.set(id, null);
      return novo;
    });
  }, []);
  const escolherTipo = useCallback((novo: TreinoNovo, tipo: TipoTreino) => {
    setSucesso(null);
    setErroLote(null);
    // Escolher outro tipo seleciona a linha; escolher o sugerido equivale a confirmar sem mudar.
    setSelecao((atual) => new Map(atual).set(novo.atividade_id, tipo === novo.tipo_sugerido ? null : tipo));
    setFolha(null);
    const origem = origemFolha.current;
    origemFolha.current = null;
    if (origem) setTimeout(() => focar(origem), 0);
  }, []);
  const todosMarcados = !!dados && dados.novos.length > 0 && selecao.size === Math.min(dados.novos.length, LIMITE_LOTE);
  const alternarTodos = () => {
    if (!dados) return;
    setSucesso(null);
    setErroLote(null);
    setSelecao(todosMarcados ? new Map() : new Map(dados.novos.slice(0, LIMITE_LOTE).map((n) => [n.atividade_id, selecao.get(n.atividade_id) ?? null])));
  };
  const limparSelecao = () => {
    setSelecao(new Map());
    setErroLote(null);
  };
  const corrigidos = [...selecao.values()].filter((v) => v !== null).length;

  const salvar = async () => {
    if (professorId === null || !dados || salvando || selecao.size === 0) return;
    // A ordem é a da API; só `atividade_id` e `tipo_treino` saem do app.
    const itens = dados.novos.filter((n) => selecao.has(n.atividade_id)).map((n) => ({ atividade_id: n.atividade_id, tipo_treino: selecao.get(n.atividade_id) ?? n.tipo_sugerido }));
    setSalvando(true);
    setErroLote(null);
    setSucesso(null);
    const r = await confirmarTiposDeTreino(professorId, itens, { baseUrl: apiUrl, fetch: fetchFn });
    setSalvando(false);
    if (r.ok) {
      const frase = textoSalvo(r.dados);
      setSelecao(new Map());
      setSucesso(frase);
      anunciar(frase);
      setTentativa((n) => n + 1); // a caixa é calculada a cada leitura: busca de novo
      return;
    }
    const codigo = codigoDoErro(r.erro);
    const erro: ErroLote =
      r.erro.tipo === "nao_encontrado" && codigo === "atividade_nao_encontrada"
        ? { texto: TEXTO_ERRO_LOTE.indisponivel, atualizar: true }
        : r.erro.tipo === "validacao" && codigo === "atividade_sem_tipo"
          ? { texto: TEXTO_ERRO_LOTE.semTipo, atualizar: true }
          : r.erro.tipo === "validacao"
            ? { texto: TEXTO_ERRO_LOTE.validacao, atualizar: false }
            : { texto: TEXTO_ERRO_LOTE.servidor, atualizar: false };
    setErroLote(erro); // a seleção e as correções ficam
    anunciar(erro.texto);
  };
  const atualizarDoErro = () => {
    setSelecao(new Map());
    setErroLote(null);
    buscarDeNovo();
  };
  /** Abre a folha guardando quem tinha o foco ("Mudar tipo" da linha), para devolvê-lo ao fechar. */
  const abrirFolha = (id: number) => {
    origemFolha.current = Platform.OS === "web" && typeof document !== "undefined" ? document.activeElement : null;
    setFolha(id);
  };
  const fecharFolha = () => {
    setFolha(null);
    const origem = origemFolha.current;
    origemFolha.current = null;
    if (origem) setTimeout(() => focar(origem), 0);
  };
  /** "Confirmar ou corrigir em Treinos novos": rola até a linha do treino e leva o foco a ela. */
  const irParaNovo = (id: number) => {
    const linha = linhasNovas.current.get(id);
    rolarAte(rolagem.current, linha);
    focar(linha);
  };
  const idsNovos = new Set(dados?.novos.map((n) => n.atividade_id) ?? []);
  const noFolha = dados?.novos.find((n) => n.atividade_id === folha) ?? null;
  const barra = selecao.size > 0 || salvando;

  return (
    <View style={styles.raiz}>
    <ScrollView ref={rolagem} testID="rolagem-tela" contentContainerStyle={[styles.container, barra && { paddingBottom: erroLote ? 240 : 150 }]}>
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
            style={comHover(styles.atualizar, styles.hover, styles.foco)}
          >
            {atualizando ? (
              <ActivityIndicator testID="atualizando" size="small" color={tema.cor.destaque} />
            ) : (
              <MaterialIcons name="refresh" size={tamanho.iconeGrande} color={podeAtualizar ? tema.cor.destaque : tema.cor["texto-desligado"]} accessible={false} />
            )}
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
        <View testID="aviso-atualizar" accessibilityRole="alert" style={styles.aviso}>
          <MaterialIcons name="error-outline" size={tamanho.iconeMedio} color={tema.cor.erro} accessible={false} />
          <Text style={styles.avisoTexto}>
            {sucesso ? "Não foi possível atualizar a lista. O que você salvou está salvo." : "Não foi possível atualizar. Você está vendo a caixa de antes."}
          </Text>
          {sucesso && (
            <Pressable accessibilityRole="button" onPress={buscarDeNovo} style={comFoco(styles.textoBotao, styles.foco)}>
              <Text style={styles.link}>Atualizar</Text>
            </Pressable>
          )}
        </View>
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
                <CartaoAluno key={aluno.atleta_id} aluno={aluno} abertos={abertos} alternar={alternar} novosIds={idsNovos} irParaNovo={irParaNovo} styles={styles} tema={tema} />
              ),
            )}
          </View>

          <View role="region" aria-label="Treinos novos" style={styles.secao}>
            <Text ref={tituloNovos} {...FOCAVEL} accessibilityRole="header" aria-level={2} style={styles.secaoTitulo}>
              Treinos novos
            </Text>
            <Text style={styles.legenda}>{`Últimos ${dados.janela_novos_dias} dias, com tipo sugerido. Confirme como está ou mude o tipo.`}</Text>
            {sucesso && (
              <View testID="sucesso-lote" style={styles.sucesso}>
                <MaterialIcons name="check-circle-outline" size={tamanho.iconeMedio} color={tema.cor.sucesso} accessible={false} />
                <Text style={styles.sucessoTexto}>{sucesso}</Text>
              </View>
            )}
            {dados.novos.length > 0 && (
              <Pressable
                testID="selecionar-todos"
                accessibilityRole="checkbox"
                accessibilityState={{ checked: todosMarcados, disabled: salvando }}
                disabled={salvando}
                onPress={alternarTodos}
                style={comHover(styles.selecionarTodos, styles.hover, styles.foco)}
              >
                <MaterialIcons name={todosMarcados ? "check-box" : "check-box-outline-blank"} size={tamanho.iconeGrande} color={todosMarcados ? tema.cor.destaque : tema.cor["borda-forte"]} accessible={false} />
                <Text style={styles.corpoForte}>{`Selecionar todos (${dados.novos.length})`}</Text>
              </Pressable>
            )}
            {dados.novos.length > LIMITE_LOTE && selecao.size >= LIMITE_LOTE && (
              <Text style={styles.legenda}>Foram selecionados os 200 primeiros. Salve e selecione os próximos.</Text>
            )}
            {dados.novos.length === 0 ? (
              <View testID="estado-sem-novos" style={styles.semNovos}>
                <MaterialIcons name="check-circle-outline" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
                <Text style={styles.texto}>Nenhum treino novo para confirmar.</Text>
              </View>
            ) : (
              dados.novos.map((n) => (
                <LinhaNovo
                  key={n.atividade_id}
                  novo={n}
                  aberto={abertos.has(`n-${n.atividade_id}`)}
                  alternar={alternar}
                  selecionado={selecao.has(n.atividade_id)}
                  corrigidoPara={selecao.get(n.atividade_id) ?? null}
                  desligado={salvando}
                  aoMarcar={() => marcar(n.atividade_id)}
                  aoMudarTipo={() => abrirFolha(n.atividade_id)}
                  refLinha={(el) => void linhasNovas.current.set(n.atividade_id, el)}
                  aoVoltar={() => setSelecao((atual) => new Map(atual).set(n.atividade_id, null))}
                  styles={styles}
                  tema={tema}
                />
              ))
            )}
          </View>
        </View>
      )}
    </ScrollView>
    {barra && <BarraLote selecionados={selecao.size} corrigidos={corrigidos} salvando={salvando} erro={erroLote} aoLimpar={limparSelecao} aoSalvar={() => void salvar()} aoAtualizar={atualizarDoErro} />}
    {noFolha && (
      <FolhaTipo
        visivel
        subtitulo={`${noFolha.atleta_nome} · ${MODALIDADES[noFolha.modalidade]?.nome ?? noFolha.modalidade} de ${dataPorExtenso(noFolha.data_local)}`}
        sugerido={noFolha.tipo_sugerido}
        escolhido={selecao.get(noFolha.atividade_id) ?? noFolha.tipo_sugerido}
        aoEscolher={(t) => escolherTipo(noFolha, t)}
        aoFechar={fecharFolha}
      />
    )}
    <Text testID="anuncio" accessibilityLiveRegion="polite" aria-live="polite" style={styles.anuncio}>
      {anuncio}
    </Text>
    </View>
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
        <Pressable accessibilityRole="button" onPress={aoTentar} style={comFoco(styles.botao, styles.foco)}>
          <Text style={styles.botaoTexto}>Tentar de novo</Text>
        </Pressable>
      )}
    </View>
  );
}

function CartaoAluno({ aluno, abertos, alternar, novosIds, irParaNovo, styles, tema }: { aluno: AlunoCaixa; abertos: ReadonlySet<string>; alternar: (c: string) => void; novosIds: ReadonlySet<number>; irParaNovo: (id: number) => void; styles: Estilos; tema: Tema }) {
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
              hitSlop={ALVO_LINHA}
              style={comHover(styles.linhaTreino, styles.hover, styles.foco)}
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
            {aberto && (
              <Detalhe
                detalhe={t.detalhe}
                testID={`detalhe-${t.atividade_id}`}
                // Só treino com divergência que ainda está em "Treinos novos" tem para onde ir.
                irParaNovo={t.motivos.some((m) => m.codigo === "divergencia") && novosIds.has(t.atividade_id) ? () => irParaNovo(t.atividade_id) : undefined}
                styles={styles}
                tema={tema}
              />
            )}
          </View>
        );
      })}
    </View>
  );
}

type PropsNovo = {
  novo: TreinoNovo;
  aberto: boolean;
  alternar: (c: string) => void;
  selecionado: boolean;
  corrigidoPara: TipoTreino | null;
  desligado: boolean;
  aoMarcar: () => void;
  aoMudarTipo: () => void;
  aoVoltar: () => void;
  refLinha: (el: ComponentRef<typeof View> | null) => void;
  styles: Estilos;
  tema: Tema;
};

function LinhaNovo({ novo, aberto, alternar, selecionado, corrigidoPara, desligado, aoMarcar, aoMudarTipo, aoVoltar, refLinha, styles, tema }: PropsNovo) {
  const mod = MODALIDADES[novo.modalidade];
  const resumo = `${mod?.nome ?? novo.modalidade} · ${novo.duracao_texto} · ${dataCurta(novo.data_local)}`;
  const rotulo = `${novo.atleta_nome}, ${mod?.nome ?? novo.modalidade}, ${novo.duracao_texto}, ${dataPorExtenso(novo.data_local)}. Tipo sugerido ${novo.tipo_sugerido_texto}, ${novo.origem_texto}.`;
  const rotuloCaixa = `Selecionar o treino de ${novo.atleta_nome}, ${mod ? mod.nome.toLowerCase() : novo.modalidade} de ${dataPorExtenso(novo.data_local)}, tipo sugerido ${novo.tipo_sugerido_texto.toLowerCase()}`;
  return (
    <View testID={`novo-${novo.atividade_id}`} style={[styles.cartao, styles.cartaoNovo, selecionado && styles.cartaoSelecionado]}>
      <Pressable
        testID={`selecionar-${novo.atividade_id}`}
        accessibilityRole="checkbox"
        accessibilityLabel={rotuloCaixa}
        accessibilityState={{ checked: selecionado, disabled: desligado }}
        disabled={desligado}
        onPress={aoMarcar}
        style={comHover(styles.caixa, styles.hover, styles.foco)}
      >
        <MaterialIcons name={selecionado ? "check-box" : "check-box-outline-blank"} size={tamanho.iconeGrande} color={selecionado ? tema.cor.destaque : tema.cor["borda-forte"]} accessible={false} />
      </Pressable>
      <View style={styles.novoCorpo}>
        <Pressable
          ref={refLinha}
          testID={`treino-novo-${novo.atividade_id}`}
          accessibilityRole="button"
          accessibilityLabel={rotulo}
          accessibilityState={{ expanded: aberto, disabled: desligado }}
          disabled={desligado}
          onPress={() => alternar(`n-${novo.atividade_id}`)}
          hitSlop={ALVO_LINHA}
          style={comHover(styles.linhaTreino, styles.hover, styles.foco)}
        >
          <View style={styles.linhaTextos}>
            <Text style={styles.corpoForte}>{novo.atleta_nome}</Text>
            <View style={styles.linhaModalidade}>
              {mod && <MaterialIcons name={mod.icone} size={tamanho.iconeMedio} color={tema.cor[mod.cor]} accessible={false} />}
              <Text style={styles.rotulo}>{resumo}</Text>
            </View>
            <View style={styles.tipoLinha}>
              <View style={[styles.chip, selecionado && styles.chipSelecionado]}>
                <Text style={styles.chipTexto}>{novo.tipo_sugerido_texto}</Text>
              </View>
              <Text style={styles.legenda}>{`(${novo.origem_texto})`}</Text>
            </View>
          </View>
          <MaterialIcons name={aberto ? "expand-less" : "expand-more"} size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
        </Pressable>
        {corrigidoPara && (
          <View testID={`corrigido-${novo.atividade_id}`} style={styles.linhaModalidade}>
            <MaterialIcons name="edit" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
            <Text style={styles.corpoForte}>{`Corrigido para ${textoDoTipo(corrigidoPara)}`}</Text>
          </View>
        )}
        <View style={styles.acoesLinha}>
          <Pressable testID={`mudar-tipo-${novo.atividade_id}`} accessibilityRole="button" disabled={desligado} onPress={aoMudarTipo} style={comHover(styles.botaoLink, styles.hover, styles.foco)}>
            <Text style={styles.link}>Mudar tipo</Text>
          </Pressable>
          {corrigidoPara && (
            <Pressable testID={`voltar-${novo.atividade_id}`} accessibilityRole="button" disabled={desligado} onPress={aoVoltar} style={comHover(styles.botaoLink, styles.hover, styles.foco)}>
              <Text style={styles.link}>Voltar à sugestão</Text>
            </Pressable>
          )}
        </View>
        {aberto && <Detalhe detalhe={novo.detalhe} testID={`detalhe-novo-${novo.atividade_id}`} styles={styles} tema={tema} />}
      </View>
    </View>
  );
}

function Detalhe({ detalhe, testID, irParaNovo, styles, tema }: { detalhe: DetalheTreino; testID: string; irParaNovo?: () => void; styles: Estilos; tema: Tema }) {
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
      {irParaNovo && (
        <Pressable testID={`ir-para-novos-${testID}`} accessibilityRole="button" onPress={irParaNovo} style={comFoco(styles.botaoLink, styles.foco)}>
          <View style={styles.linhaModalidade}>
            <Text style={styles.link}>Confirmar ou corrigir em Treinos novos</Text>
            <MaterialIcons name="chevron-right" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
          </View>
        </Pressable>
      )}
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
    raiz: { flex: 1 },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
    anuncio: { position: "absolute", width: 1, height: 1, overflow: "hidden", opacity: 0 },
    cartaoNovo: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2], paddingLeft: espaco[1] },
    cartaoSelecionado: { backgroundColor: cor["destaque-suave"], borderColor: cor.destaque, borderWidth: 2 },
    caixa: { width: 48, minHeight: 72, alignItems: "center", paddingTop: espaco[3] },
    novoCorpo: { flex: 1, gap: espaco[2] },
    acoesLinha: { flexDirection: "row", flexWrap: "wrap", gap: espaco[3] },
    botaoLink: { minHeight: tamanho.alvoMinimo, justifyContent: "center", paddingHorizontal: espaco[1], borderRadius: raio.medio },
    link: { ...fonte.botao, color: cor.destaque },
    textoBotao: { minHeight: tamanho.alvoMinimo, justifyContent: "center" },
    selecionarTodos: { minHeight: tamanho.alvoMinimo, flexDirection: "row", alignItems: "center", gap: espaco[2], marginTop: espaco[2], borderRadius: raio.medio },
    sucesso: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2], backgroundColor: cor["sucesso-suave"], padding: espaco[3], borderRadius: raio.medio, marginTop: espaco[3] },
    sucessoTexto: { ...fonte.corpo, color: cor.sucesso, flex: 1 },
    chipSelecionado: { backgroundColor: cor.superficie },
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
    linhaTreino: { flexDirection: "row", alignItems: "flex-start", gap: espaco[3], borderRadius: raio.medio },
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
    aviso: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2], backgroundColor: cor["erro-suave"], padding: espaco[3], borderRadius: raio.medio, marginTop: espaco[3] },
    avisoTexto: { ...fonte.corpo, color: cor.erro, flex: 1 },
    estado: { alignItems: "center", paddingVertical: espaco[7], gap: espaco[2] },
    estadoTitulo: { ...fonte["titulo-secao"], color: cor.texto, textAlign: "center" },
    botao: { minHeight: tamanho.botaoAltura, justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.medio, backgroundColor: cor.destaque, marginTop: espaco[3] },
    botaoTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
  });
}
