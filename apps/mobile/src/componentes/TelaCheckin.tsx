// Tela do check-in pós-treino (#299, spec docs/design/telas/checkin.md, ADR 0012).
// Criar: uma pergunta por vez, o PUT sai uma vez no fim. Editar: tela única com "Mudar". Nenhum rascunho é guardado
// e nenhuma resposta vai para log, console, URL ou armazenamento (ADR 0012, item 5).
import { MaterialIcons } from "@expo/vector-icons";
import { buscarAtividade, type Atividade, type Checkin, type ErroApi } from "@treino/api-client";
import { useCallback, useEffect, useMemo, useRef, useState, type ComponentRef, type ReactNode } from "react";
import {
  AccessibilityInfo,
  ActivityIndicator,
  BackHandler,
  findNodeHandle,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { apagarCheckin, motivo422, registrarCheckin } from "../checkin/api";
import {
  AVISO_TEXTO,
  LIMITE_TEXTO,
  TEXTO_SEM_CHECKIN_ELEGIVEL,
  avisoPseSugerida,
  checkinCompleto,
  montarEnvio,
  observacaoDoCheckin,
  pseComAncora,
  pseDoCheckin,
  pseFalada,
  temConteudoSensivel,
  textoForaDoPrazo,
  SENSACOES,
  type ChaveAtalho,
  type Observacao,
} from "../checkin/escala";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";
import { ChipsAtalhos, Dialogo, Folha, GradePse, ListaSensacao } from "./CheckinOpcoes";
import { EsqueletoCheckin } from "./Esqueleto";
import { dataCurta } from "./GraficoTiros";
import { MODALIDADES } from "./modalidades";

export type OrigemCheckin = "treino" | "pendentes";

type Props = {
  apiUrl: string;
  atletaId: number;
  atividadeId: number;
  /** Sai da tela sem salvar (Voltar na pergunta 1 ou na edição). */
  aoVoltar?: () => void;
  /** Depois de salvar: "Voltar ao treino" ou "Voltar aos pendentes". */
  aoConcluir?: () => void;
  /** Depois de apagar o check-in (volta ao treino, que mostra o cartão sem check-in). */
  aoApagado?: () => void;
  /** De onde a pessoa veio; só muda o texto do botão de "Salvo". */
  origem?: OrigemCheckin;
  /** Troque nos testes. Padrão: o fetch global. */
  fetchFn?: typeof fetch;
};

type Carga =
  | { tipo: "carregando" }
  | { tipo: "ok"; atividade: Atividade }
  | { tipo: "erro"; erro: ErroApi }
  | { tipo: "aviso"; texto: string };

type Passo = 1 | 2 | 3;
type Dialogos = "nada" | "sair" | "apagar" | null;
const OBS_VAZIA: Observacao = { nadaARelatar: false, atalhos: [], texto: "" };

function mensagemCarga(erro: ErroApi): string {
  switch (erro.tipo) {
    case "nao_encontrado":
      return erro.detalhe.detail === "atleta não encontrado" ? "Atleta não encontrado" : "Treino não encontrado";
    case "rede":
      return "Não foi possível falar com o servidor";
    default:
      return "Não foi possível carregar o check-in. Tente de novo mais tarde.";
  }
}

/** Erro ao salvar (não ao carregar): texto fixo, nunca o `detail` da API. */
function mensagemSalvar(erro: ErroApi): string {
  switch (erro.tipo) {
    case "rede":
      return "Não foi possível falar com o servidor. Suas respostas continuam aqui. Tente salvar de novo.";
    case "validacao":
      return "Algum dado do check-in não foi aceito. Confira as respostas e tente de novo.";
    case "nao_encontrado":
      return "Treino não encontrado.";
    default:
      return "Não foi possível salvar. Tente de novo mais tarde.";
  }
}

function anunciar(texto: string) {
  try {
    AccessibilityInfo.announceForAccessibility?.(texto);
  } catch {
    // sem leitor de tela disponível
  }
}

const PERGUNTAS: Record<Passo, string> = {
  1: "Qual foi o esforço do treino?",
  2: "Como você se sentiu no treino?",
  3: "Quer registrar mais alguma coisa?",
};

function observacaoDe(c: Checkin): Observacao {
  return { nadaARelatar: c.nada_a_relatar, atalhos: c.atalhos.map((a) => a.chave), texto: c.texto ?? "" };
}

export function TelaCheckin({ apiUrl, atletaId, atividadeId, aoVoltar, aoConcluir, aoApagado, origem = "treino", fetchFn }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const opcoes = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);

  const [carga, setCarga] = useState<Carga>({ tipo: "carregando" });
  const [tentativa, setTentativa] = useState(0);
  const [passo, setPasso] = useState<Passo>(1);
  const [pse, setPse] = useState<number | null>(null);
  const [sensacao, setSensacao] = useState<number | null>(null);
  const [obs, setObs] = useState<Observacao>(OBS_VAZIA);
  const [original, setOriginal] = useState<Checkin | null>(null);
  const [folha, setFolha] = useState<"pse" | "sensacao" | null>(null);
  const [dialogo, setDialogo] = useState<Dialogos>(null);
  const [acao, setAcao] = useState<"salvando" | "apagando" | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [salvo, setSalvo] = useState<Checkin | null>(null);

  useEffect(() => {
    let ativo = true;
    buscarAtividade(atletaId, atividadeId, opcoes).then((r) => {
      if (!ativo) return;
      if (!r.ok) return setCarga({ tipo: "erro", erro: r.erro });
      const a = r.dados;
      if (a.checkin) {
        setOriginal(a.checkin);
        setPse(a.checkin.pse);
        setSensacao(a.checkin.sensacao);
        setObs(observacaoDe(a.checkin));
        return setCarga({ tipo: "ok", atividade: a });
      }
      if (!a.checkin_aberto) {
        const semCheckin = a.subtipo === "multiesporte_pai" || a.subtipo === "troca";
        return setCarga({ tipo: "aviso", texto: semCheckin ? TEXTO_SEM_CHECKIN_ELEGIVEL : textoForaDoPrazo() });
      }
      setCarga({ tipo: "ok", atividade: a });
    });
    return () => {
      ativo = false;
    };
  }, [atletaId, atividadeId, opcoes, tentativa]);

  const editando = original !== null;
  const concluido = salvo !== null;
  const sensivel = temConteudoSensivel(obs);
  const envioAtual = pse !== null && sensacao !== null ? montarEnvio(pse, sensacao, obs) : null;
  const mudou = useMemo(() => {
    if (!original || !envioAtual) return false;
    return JSON.stringify(envioAtual) !== JSON.stringify(montarEnvio(original.pse, original.sensacao, observacaoDe(original)));
  }, [original, envioAtual]);
  const precisaConfirmarSaida = sensivel && !concluido && (editando ? mudou : true);

  const voltarAtras = useCallback(() => {
    if (acao) return;
    if (!editando && passo > 1 && carga.tipo === "ok" && !concluido) return setPasso((p) => (p - 1) as Passo);
    if (precisaConfirmarSaida) return setDialogo("sair");
    aoVoltar?.();
  }, [acao, editando, passo, carga.tipo, concluido, precisaConfirmarSaida, aoVoltar]);

  useEffect(() => {
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      voltarAtras();
      return true;
    });
    return () => sub.remove();
  }, [voltarAtras]);

  // Na web, fechar a aba com texto digitado pede confirmação do navegador.
  useEffect(() => {
    if (Platform.OS !== "web" || typeof window === "undefined" || !precisaConfirmarSaida) return;
    const aviso = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", aviso);
    return () => window.removeEventListener("beforeunload", aviso);
  }, [precisaConfirmarSaida]);

  const salvar = useCallback(
    async (p: number, s: number, o: Observacao) => {
      setErroAcao(null);
      setAcao("salvando");
      const r = await registrarCheckin(atletaId, atividadeId, montarEnvio(p, s, o), opcoes);
      setAcao(null);
      if (r.ok) {
        setSalvo(r.dados);
        return anunciar("Check-in salvo.");
      }
      if (r.erro.tipo === "validacao") {
        const motivo = motivo422(r.erro);
        if (motivo === "fora_do_prazo") return setCarga({ tipo: "aviso", texto: textoForaDoPrazo() });
        if (motivo === "atividade_sem_checkin") return setCarga({ tipo: "aviso", texto: TEXTO_SEM_CHECKIN_ELEGIVEL });
      }
      setErroAcao(mensagemSalvar(r.erro));
    },
    [atletaId, atividadeId, opcoes],
  );

  const apagar = useCallback(async () => {
    setDialogo(null);
    setErroAcao(null);
    setAcao("apagando");
    const r = await apagarCheckin(atletaId, atividadeId, opcoes);
    setAcao(null);
    if (r.ok) {
      anunciar("Check-in apagado.");
      return aoApagado?.();
    }
    setErroAcao("Não foi possível apagar. Tente de novo.");
  }, [atletaId, atividadeId, opcoes, aoApagado]);

  const escolherPse = (n: number) => {
    setPse(n);
    if (!editando) {
      setPasso(2);
      anunciar(`Escolhido: ${pseFalada(n)}. Pergunta 2 de 3: ${PERGUNTAS[2].toLowerCase()}`);
    } else setFolha(null);
  };
  const escolherSensacao = (n: number) => {
    setSensacao(n);
    if (!editando) {
      setPasso(3);
      const nome = SENSACOES.find((x) => x.valor === n)?.texto.toLowerCase() ?? "";
      anunciar(`Escolhido: sensação, ${nome}. Pergunta 3 de 3: ${PERGUNTAS[3].toLowerCase()}`);
    } else setFolha(null);
  };
  const alternarAtalho = (c: ChaveAtalho) =>
    setObs((o) => ({
      ...o,
      nadaARelatar: false,
      atalhos: o.atalhos.includes(c) ? o.atalhos.filter((x) => x !== c) : [...o.atalhos, c],
    }));
  const digitar = (texto: string) => setObs((o) => ({ ...o, nadaARelatar: false, texto }));
  const nadaARelatar = () => {
    if (temConteudoSensivel(obs)) return setDialogo("nada");
    if (editando) return setObs({ ...OBS_VAZIA, nadaARelatar: !obs.nadaARelatar });
    if (pse !== null && sensacao !== null) void salvar(pse, sensacao, { ...OBS_VAZIA, nadaARelatar: true });
  };
  const confirmarNada = () => {
    setDialogo(null);
    const vazia = { ...OBS_VAZIA, nadaARelatar: true };
    setObs(vazia);
    if (!editando && pse !== null && sensacao !== null) void salvar(pse, sensacao, vazia);
  };

  const atividade = carga.tipo === "ok" ? carga.atividade : null;
  const mod = atividade ? MODALIDADES[atividade.modalidade] : undefined;
  const ocupado = acao !== null;
  const completo = checkinCompleto(pse, sensacao, obs);

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.raiz}>
      <ScrollView testID="rolagem-tela" keyboardShouldPersistTaps="handled" contentContainerStyle={styles.container}>
        <Pressable accessibilityRole="button" accessibilityLabel="Voltar" onPress={voltarAtras} style={styles.voltar}>
          <MaterialIcons name="arrow-back" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
          <Text style={styles.voltarTexto}>Voltar</Text>
        </Pressable>

        {carga.tipo === "carregando" && (
          <View>
            <Text accessibilityLiveRegion="polite" style={[styles.texto, { marginTop: espaco[2] }]}>
              Carregando o check-in...
            </Text>
            <EsqueletoCheckin />
          </View>
        )}

        {carga.tipo === "erro" && (
          <View testID="estado-erro" style={styles.estado}>
            <MaterialIcons
              name={carga.erro.tipo === "rede" ? "wifi-off" : "error-outline"}
              size={tamanho.iconeEstado}
              color={tema.cor.erro}
              accessible={false}
            />
            <Text accessibilityRole="alert" style={styles.erroTexto}>
              {mensagemCarga(carga.erro)}
            </Text>
            {carga.erro.tipo === "rede" && (
              <Pressable
                accessibilityRole="button"
                onPress={() => {
                  setCarga({ tipo: "carregando" });
                  setTentativa((n) => n + 1);
                }}
                style={styles.botaoPrimario}
              >
                <Text style={styles.botaoPrimarioTexto}>Tentar de novo</Text>
              </Pressable>
            )}
          </View>
        )}

        {carga.tipo === "aviso" && (
          <View testID="estado-aviso" style={styles.estado}>
            <MaterialIcons name="error-outline" size={tamanho.iconeEstado} color={tema.cor.erro} accessible={false} />
            <Text accessibilityRole="alert" style={styles.erroTexto}>
              {carga.texto}
            </Text>
            <Pressable accessibilityRole="button" onPress={() => (aoConcluir ?? aoVoltar)?.()} style={styles.botaoPrimario}>
              <Text style={styles.botaoPrimarioTexto}>Voltar ao treino</Text>
            </Pressable>
          </View>
        )}

        {atividade && salvo && (
          <View testID="estado-salvo" style={styles.estado}>
            <MaterialIcons name="check-circle-outline" size={tamanho.iconeEstado} color={tema.cor.sucesso} accessible={false} />
            <Text accessibilityRole="header" style={styles.tituloSecao}>
              Check-in salvo
            </Text>
            <Resumo checkin={salvo} styles={styles} />
            <Pressable accessibilityRole="button" onPress={() => (aoConcluir ?? aoVoltar)?.()} style={styles.botaoPrimario}>
              <Text style={styles.botaoPrimarioTexto}>{origem === "pendentes" ? "Voltar aos pendentes" : "Voltar ao treino"}</Text>
            </Pressable>
          </View>
        )}

        {atividade && !salvo && (
          <View>
            <Text accessibilityRole="header" style={styles.titulo}>
              {editando ? "Editar check-in" : "Check-in do treino"}
            </Text>
            <View style={styles.cabecalho}>
              {mod && (
                <View testID="chip-modalidade" style={styles.chip}>
                  <MaterialIcons name={mod.icone} size={tamanho.iconePequeno} color={tema.cor[mod.cor]} accessible={false} />
                  <Text style={styles.chipTexto}>{mod.nome}</Text>
                </View>
              )}
              <Text style={styles.rotulo}>
                {atividade.duracao} · {dataCurta(atividade.data_local)}
              </Text>
            </View>

            {editando ? (
              <Edicao
                styles={styles}
                tema={tema}
                pse={pse}
                sensacao={sensacao}
                obs={obs}
                ocupado={ocupado}
                acao={acao}
                podeSalvar={mudou && completo}
                erro={erroAcao}
                aoMudar={setFolha}
                aoAlternarAtalho={alternarAtalho}
                aoDigitar={digitar}
                aoNada={nadaARelatar}
                aoSalvar={() => pse !== null && sensacao !== null && void salvar(pse, sensacao, obs)}
                aoApagar={() => setDialogo("apagar")}
              />
            ) : (
              <Pergunta
                passo={passo}
                styles={styles}
                tema={tema}
                sugerida={atividade.pse_sugerida ?? null}
                pse={pse}
                sensacao={sensacao}
                obs={obs}
                ocupado={ocupado}
                acao={acao}
                completo={completo}
                erro={erroAcao}
                aoPse={escolherPse}
                aoSensacao={escolherSensacao}
                aoAlternarAtalho={alternarAtalho}
                aoDigitar={digitar}
                aoNada={nadaARelatar}
                aoSalvar={() => pse !== null && sensacao !== null && void salvar(pse, sensacao, obs)}
              />
            )}
          </View>
        )}
      </ScrollView>

      <Folha visivel={folha === "pse"} titulo="Esforço (PSE)" fechar={() => setFolha(null)}>
        <GradePse valor={pse} aoEscolher={escolherPse} />
      </Folha>
      <Folha visivel={folha === "sensacao"} titulo="Sensação" fechar={() => setFolha(null)}>
        <ListaSensacao valor={sensacao} aoEscolher={escolherSensacao} />
      </Folha>

      <Dialogo
        visivel={dialogo === "nada"}
        titulo="Descartar o que você marcou?"
        texto="Nada a relatar apaga os atalhos e o texto desta pergunta."
        primaria={{ rotulo: "Cancelar", aoPress: () => setDialogo(null) }}
        secundaria={{ rotulo: "Nada a relatar", aoPress: confirmarNada }}
        aoFechar={() => setDialogo(null)}
      />
      <Dialogo
        visivel={dialogo === "sair"}
        titulo="Sair sem salvar?"
        texto="O que você escreveu aqui será perdido."
        primaria={{ rotulo: "Continuar", aoPress: () => setDialogo(null) }}
        secundaria={{
          rotulo: "Sair",
          aoPress: () => {
            setDialogo(null);
            aoVoltar?.();
          },
        }}
        aoFechar={() => setDialogo(null)}
      />
      <Dialogo
        visivel={dialogo === "apagar"}
        titulo="Apagar este check-in?"
        texto="A PSE, a sensação e a observação deste treino serão apagadas. Isso não pode ser desfeito."
        primaria={{ rotulo: "Cancelar", aoPress: () => setDialogo(null) }}
        secundaria={{ rotulo: "Apagar", aoPress: () => void apagar(), perigo: true }}
        aoFechar={() => setDialogo(null)}
      />
    </KeyboardAvoidingView>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function Resumo({ checkin, styles }: { checkin: Checkin; styles: Estilos }) {
  const o = observacaoDoCheckin(checkin);
  return (
    <View style={styles.resumo}>
      <Text style={styles.corpo}>Esforço (PSE): {pseDoCheckin(checkin)}</Text>
      <Text style={styles.corpo}>Sensação: {checkin.sensacao_texto}</Text>
      <Text style={styles.corpo}>Observação: {o.linha}</Text>
      {o.texto ? <Text style={styles.secundario}>{o.texto}</Text> : null}
    </View>
  );
}

function Pergunta(props: {
  passo: Passo;
  styles: Estilos;
  tema: Tema;
  sugerida: number | null;
  pse: number | null;
  sensacao: number | null;
  obs: Observacao;
  ocupado: boolean;
  acao: "salvando" | "apagando" | null;
  completo: boolean;
  erro: string | null;
  aoPse: (n: number) => void;
  aoSensacao: (n: number) => void;
  aoAlternarAtalho: (c: ChaveAtalho) => void;
  aoDigitar: (t: string) => void;
  aoNada: () => void;
  aoSalvar: () => void;
}) {
  const { passo, styles, tema, ocupado } = props;
  // Leva o foco ao título da pergunta nova (não na primeira vez).
  const tituloRef = useRef<ComponentRef<typeof Text>>(null);
  const primeiroPasso = useRef(true);
  useEffect(() => {
    if (primeiroPasso.current) {
      primeiroPasso.current = false;
      return;
    }
    try {
      const h = findNodeHandle(tituloRef.current);
      if (h != null) AccessibilityInfo.setAccessibilityFocus?.(h);
    } catch {
      // sem foco programático nesta plataforma
    }
  }, [passo]);
  return (
    <View>
      <View style={styles.progresso} accessible accessibilityLabel={`Pergunta ${passo} de 3`}>
        <Text style={styles.rotulo}>Pergunta {passo} de 3</Text>
        <View style={styles.segmentos}>
          {[1, 2, 3].map((n) => (
            <View key={n} style={[styles.segmento, n <= passo && { backgroundColor: tema.cor.destaque }]} />
          ))}
        </View>
      </View>
      <Text ref={tituloRef} accessibilityRole="header" style={styles.pergunta}>
        {PERGUNTAS[passo]}
      </Text>

      {passo === 1 && (
        <View>
          <Text style={styles.legenda}>0 é repouso e 10 é o máximo. É a sua percepção.</Text>
          {props.sugerida !== null && (
            <View testID="pse-sugerida" style={styles.aviso}>
              <MaterialIcons name="info-outline" size={tamanho.iconeMedio} color={tema.cor.texto} accessible={false} />
              <Text style={styles.avisoTexto}>{avisoPseSugerida(props.sugerida)}</Text>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`Usar ${props.sugerida}`}
                onPress={() => props.aoPse(props.sugerida as number)}
                style={styles.botaoTexto}
              >
                <Text style={styles.botaoTextoRotulo}>Usar {props.sugerida}</Text>
              </Pressable>
            </View>
          )}
          <GradePse valor={props.pse} aoEscolher={props.aoPse} />
          <Text style={[styles.legenda, { marginTop: espaco[3] }]}>A PSE é só sua: não se compara com a de outros atletas.</Text>
        </View>
      )}

      {passo === 2 && <ListaSensacao valor={props.sensacao} aoEscolher={props.aoSensacao} />}

      {passo === 3 && (
        <View>
          <Text style={styles.legenda}>Toque no que combina. Pode marcar mais de um.</Text>
          <ChipsAtalhos marcados={props.obs.atalhos} aoAlternar={props.aoAlternarAtalho} desligado={ocupado} />
          <CampoObservacao styles={styles} tema={tema} texto={props.obs.texto} aoDigitar={props.aoDigitar} desligado={ocupado} />
          {props.erro && <Aviso erro styles={styles} tema={tema} texto={props.erro} />}
          {!(props.obs.atalhos.length > 0 || props.obs.texto.trim().length > 0) && (
            <Text style={[styles.legenda, { marginTop: espaco[3] }]}>Marque um atalho, escreva algo ou toque em Nada a relatar.</Text>
          )}
          <Pressable
            testID="salvar-checkin"
            accessibilityRole="button"
            accessibilityState={{ disabled: !props.completo || ocupado }}
            disabled={!props.completo || ocupado}
            onPress={props.aoSalvar}
            style={[styles.botaoPrimario, styles.larguraTotal, (!props.completo || ocupado) && styles.botaoDesligado]}
          >
            <Rotulo styles={styles} tema={tema} ocupado={props.acao === "salvando"} ocupadoTexto="Salvando..." texto="Salvar check-in" />
          </Pressable>
          <Pressable
            testID="nada-a-relatar"
            accessibilityRole="button"
            accessibilityState={{ disabled: ocupado }}
            disabled={ocupado}
            onPress={props.aoNada}
            style={[styles.botaoSecundario, styles.larguraTotal, { marginTop: espaco[2] }]}
          >
            <Text style={styles.botaoSecundarioTexto}>Nada a relatar</Text>
          </Pressable>
          <Text style={[styles.legenda, { marginTop: espaco[2] }]}>Nada a relatar salva na hora.</Text>
        </View>
      )}
    </View>
  );
}

function Rotulo({ styles, tema, ocupado, ocupadoTexto, texto }: { styles: Estilos; tema: Tema; ocupado: boolean; ocupadoTexto: string; texto: string }) {
  return ocupado ? (
    <View style={styles.linhaCentro}>
      <ActivityIndicator color={tema.cor["sobre-destaque"]} />
      <Text style={styles.botaoPrimarioTexto}>{ocupadoTexto}</Text>
    </View>
  ) : (
    <Text style={styles.botaoPrimarioTexto}>{texto}</Text>
  );
}

function Aviso({ styles, tema, texto, erro }: { styles: Estilos; tema: Tema; texto: string; erro?: boolean }) {
  return (
    <View accessible={erro ? true : undefined} accessibilityRole={erro ? "alert" : undefined} style={[styles.aviso, erro && { backgroundColor: tema.cor["erro-suave"] }]}>
      <MaterialIcons name={erro ? "error-outline" : "info-outline"} size={tamanho.iconeMedio} color={erro ? tema.cor.erro : tema.cor.texto} accessible={false} />
      <Text style={[styles.avisoTexto, erro && { color: tema.cor.erro }]}>{texto}</Text>
    </View>
  );
}

function CampoObservacao({
  styles,
  tema,
  texto,
  aoDigitar,
  desligado,
}: {
  styles: Estilos;
  tema: Tema;
  texto: string;
  aoDigitar: (t: string) => void;
  desligado?: boolean;
}) {
  const alto = texto.length > AVISO_TEXTO;
  return (
    <View>
      <Text style={[styles.rotulo, { marginTop: espaco[4] }]}>Quer acrescentar algo? (opcional)</Text>
      <TextInput
        testID="campo-texto"
        accessibilityLabel="Quer acrescentar algo? (opcional)"
        multiline
        numberOfLines={3}
        maxLength={LIMITE_TEXTO}
        editable={!desligado}
        value={texto}
        onChangeText={aoDigitar}
        autoComplete="off"
        autoCorrect={false}
        textAlignVertical="top"
        placeholderTextColor={tema.cor["texto-2"]}
        style={styles.campo}
      />
      <View style={styles.contador} accessibilityLiveRegion={alto ? "polite" : "none"}>
        {alto && <MaterialIcons name="warning-amber" size={tamanho.iconePequeno} color={tema.cor.alerta} accessible={false} />}
        <Text style={[styles.legenda, alto && { color: tema.cor.alerta }]}>
          {texto.length} de {LIMITE_TEXTO}
        </Text>
      </View>
    </View>
  );
}

function Bloco({ titulo, children, styles }: { titulo: string; children: ReactNode; styles: Estilos }) {
  return (
    <View style={styles.cartao}>
      <Text accessibilityRole="header" style={styles.cartaoTitulo}>
        {titulo}
      </Text>
      {children}
    </View>
  );
}

function Edicao(props: {
  styles: Estilos;
  tema: Tema;
  pse: number | null;
  sensacao: number | null;
  obs: Observacao;
  ocupado: boolean;
  acao: "salvando" | "apagando" | null;
  podeSalvar: boolean;
  erro: string | null;
  aoMudar: (f: "pse" | "sensacao") => void;
  aoAlternarAtalho: (c: ChaveAtalho) => void;
  aoDigitar: (t: string) => void;
  aoNada: () => void;
  aoSalvar: () => void;
  aoApagar: () => void;
}) {
  const { styles, tema, ocupado } = props;
  const sens = SENSACOES.find((s) => s.valor === props.sensacao);
  const botaoMudar = (alvo: "pse" | "sensacao", rotulo: string) => (
    <Pressable
      testID={`mudar-${alvo}`}
      accessibilityRole="button"
      accessibilityLabel={`Mudar ${rotulo}`}
      disabled={ocupado}
      onPress={() => props.aoMudar(alvo)}
      style={styles.mudar}
    >
      <MaterialIcons name="edit" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
      <Text style={styles.botaoTextoRotulo}>Mudar</Text>
    </Pressable>
  );
  return (
    <View>
      <Bloco titulo="Esforço (PSE)" styles={styles}>
        <View style={styles.linhaResumo}>
          <Text testID="resumo-pse" style={styles.corpoForte}>
            {props.pse !== null ? pseComAncora(props.pse) : ""}
          </Text>
          {botaoMudar("pse", "esforço")}
        </View>
      </Bloco>
      <Bloco titulo="Sensação" styles={styles}>
        <View style={styles.linhaResumo}>
          <View style={styles.linhaCentro}>
            {sens && <MaterialIcons name={sens.icone} size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />}
            <Text testID="resumo-sensacao" style={styles.corpoForte}>
              {sens?.texto ?? ""}
            </Text>
          </View>
          {botaoMudar("sensacao", "sensação")}
        </View>
      </Bloco>
      <Bloco titulo="Observação" styles={styles}>
        <ChipsAtalhos marcados={props.obs.atalhos} aoAlternar={props.aoAlternarAtalho} desligado={ocupado} />
        <CampoObservacao styles={styles} tema={tema} texto={props.obs.texto} aoDigitar={props.aoDigitar} desligado={ocupado} />
        <Pressable
          testID="nada-a-relatar"
          accessibilityRole="radio"
          accessibilityLabel="Nada a relatar"
          accessibilityState={{ checked: props.obs.nadaARelatar, disabled: ocupado }}
          disabled={ocupado}
          onPress={props.aoNada}
          style={styles.radioLinha}
        >
          <MaterialIcons
            name={props.obs.nadaARelatar ? "radio-button-checked" : "radio-button-unchecked"}
            size={tamanho.iconeGrande}
            color={props.obs.nadaARelatar ? tema.cor.destaque : tema.cor["texto-2"]}
            accessible={false}
          />
          <Text style={styles.corpo}>Nada a relatar</Text>
        </Pressable>
      </Bloco>
      {props.erro && <Aviso erro styles={styles} tema={tema} texto={props.erro} />}
      <Pressable
        testID="salvar-alteracoes"
        accessibilityRole="button"
        accessibilityState={{ disabled: !props.podeSalvar || ocupado }}
        disabled={!props.podeSalvar || ocupado}
        onPress={props.aoSalvar}
        style={[styles.botaoPrimario, styles.larguraTotal, { marginTop: espaco[4] }, (!props.podeSalvar || ocupado) && styles.botaoDesligado]}
      >
        <Rotulo styles={styles} tema={tema} ocupado={props.acao === "salvando"} ocupadoTexto="Salvando..." texto="Salvar alterações" />
      </Pressable>
      <Pressable
        testID="apagar-checkin"
        accessibilityRole="button"
        accessibilityState={{ disabled: ocupado }}
        disabled={ocupado}
        onPress={props.aoApagar}
        style={[styles.botaoTexto, styles.larguraTotal, { marginTop: espaco[2] }]}
      >
        <Text style={[styles.botaoTextoRotulo, { color: tema.cor.erro }]}>{props.acao === "apagando" ? "Apagando..." : "Apagar check-in"}</Text>
      </Pressable>
    </View>
  );
}

function criarEstilos({ cor }: Tema, margem: number = espaco[4]) {
  const botao = { minHeight: tamanho.botaoAltura, justifyContent: "center", alignItems: "center", paddingHorizontal: espaco[4], borderRadius: raio.medio } as const;
  return StyleSheet.create({
    raiz: { flex: 1, backgroundColor: cor.fundo },
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
    tituloSecao: { ...fonte["titulo-secao"], color: cor.texto },
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
    rotulo: { ...fonte.rotulo, color: cor["texto-2"] },
    legenda: { ...fonte.legenda, color: cor["texto-2"] },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    corpo: { ...fonte.corpo, color: cor.texto },
    corpoForte: { ...fonte["corpo-forte"], color: cor.texto },
    secundario: { ...fonte.corpo, color: cor["texto-2"] },
    progresso: { marginTop: espaco[4], gap: espaco[2] },
    segmentos: { flexDirection: "row", gap: espaco[1] },
    segmento: { flex: 1, height: 6, borderRadius: raio.pilula, backgroundColor: cor["superficie-2"] },
    pergunta: { ...fonte["titulo-secao"], color: cor.texto, marginTop: espaco[3] },
    estado: { alignItems: "center", paddingVertical: espaco[7], gap: espaco[3] },
    erroTexto: { ...fonte.corpo, color: cor.erro, textAlign: "center" },
    resumo: { alignSelf: "stretch", gap: espaco[1] },
    aviso: {
      flexDirection: "row",
      alignItems: "center",
      flexWrap: "wrap",
      gap: espaco[2],
      marginTop: espaco[3],
      padding: espaco[3],
      borderRadius: raio.medio,
      backgroundColor: cor["superficie-2"],
    },
    avisoTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    botaoPrimario: { ...botao, backgroundColor: cor.destaque, alignSelf: "flex-start" },
    botaoPrimarioTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    botaoDesligado: { backgroundColor: cor["superficie-2"] },
    botaoSecundario: { ...botao, borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    botaoSecundarioTexto: { ...fonte.botao, color: cor.texto },
    botaoTexto: { ...botao, flexDirection: "row", gap: espaco[1], minWidth: tamanho.alvoMinimo },
    botaoTextoRotulo: { ...fonte.botao, color: cor.destaque },
    larguraTotal: { alignSelf: "stretch", marginTop: espaco[4] },
    linhaCentro: { flexDirection: "row", alignItems: "center", gap: espaco[2] },
    campo: {
      minHeight: 96,
      marginTop: espaco[2],
      padding: espaco[3],
      ...fonte.corpo,
      color: cor.texto,
      borderRadius: raio.medio,
      borderWidth: borda.fina,
      borderColor: cor["borda-forte"],
      backgroundColor: cor.superficie,
    },
    contador: { flexDirection: "row", alignItems: "center", justifyContent: "flex-end", gap: espaco[1], marginTop: espaco[1] },
    cartao: {
      marginTop: espaco[4],
      padding: espaco[4],
      borderRadius: raio.grande,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    cartaoTitulo: { ...fonte["titulo-secao"], color: cor.texto },
    linhaResumo: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", minHeight: tamanho.alvoMinimo, gap: espaco[2] },
    mudar: { flexDirection: "row", alignItems: "center", gap: espaco[1], minHeight: tamanho.alvoMinimo, paddingHorizontal: espaco[2] },
    radioLinha: { flexDirection: "row", alignItems: "center", gap: espaco[2], minHeight: tamanho.botaoAltura, marginTop: espaco[2] },
  });
}
