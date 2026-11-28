// API falsa com dados 100% sintéticos, só para abrir o app na web e tirar capturas
// sem backend e sem trocar config (#218). Uso: node scripts/api-falsa.mjs [porta]
// Depois: EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start --web  (entre com atleta1@exemplo.com ou professor1@exemplo.com, senha senha-sintetica-123)
import { createServer } from "node:http";

const porta = Number(process.argv[2] ?? process.env.PORT ?? 8000);

const pace = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
const datas = ["2025-02-04", "2025-02-18", "2025-03-04", "2025-03-18"];
const melhores = [262, 258, 255, 251];
const sessoes = datas.map((data, i) => {
  const tiros = [0, 1, 2, 3, 4].map((o) => {
    const s = melhores[i] + (o === 2 ? 0 : 3 + o * 2);
    return { ordem: o + 1, distancia_m: 1000, duracao_s: s, fc_media: 168 + o, pace: pace(s), pace_s_km: s };
  });
  const medio = Math.round(tiros.reduce((t, x) => t + x.pace_s_km, 0) / tiros.length);
  return {
    atividade_id: 101 + i,
    data,
    inicio: `${data}T09:30:00Z`,
    fc_media: 160,
    fc_melhor_tiro: 170,
    n_tiros: 5,
    ordem_melhor_tiro: 3,
    pace_melhor: pace(melhores[i]),
    pace_melhor_s_km: melhores[i],
    pace_medio: pace(medio),
    pace_medio_s_km: medio,
    tiros,
  };
});

// Evolução v1 (#582, ADR 0004 adendo 15): catálogo e séries sintéticos, no formato da API (textos prontos; o app não calcula).
const CATALOGO = [
  { id: "corrida.pace.leve", titulo: "Pace dos treinos leves", descricao: "Quanto tempo você leva por quilômetro nos treinos leves", modalidade: "corrida", grupo: "Ritmo", n_pontos: 12, disponivel: true, motivo: null },
  { id: "corrida.tiros", titulo: "Melhor tiro de 1 km", descricao: "O seu tiro mais rápido de cada sessão", modalidade: "corrida", grupo: "Ritmo", n_pontos: 2, disponivel: false, motivo: "Poucos treinos de tiros nas últimas 12 semanas" },
  { id: "corrida.fc.moderado", titulo: "FC dos treinos moderados", descricao: "A frequência cardíaca média nos treinos moderados", modalidade: "corrida", grupo: "Coração", n_pontos: 9, disponivel: true, motivo: null },
  { id: "corrida.volume_km", titulo: "Volume por semana", descricao: "Quantos quilômetros você correu em cada semana", modalidade: "corrida", grupo: "Esforço e volume", n_pontos: 12, disponivel: true, motivo: null },
  { id: "natacao.ritmo", titulo: "Ritmo na piscina", descricao: "Tempo por 100 m, com pausas", modalidade: "natacao", grupo: "Ritmo", n_pontos: 9, disponivel: true, motivo: null },
  { id: "ciclismo.velocidade.rua", titulo: "Velocidade na rua", descricao: "Velocidade média nos treinos ao ar livre", modalidade: "ciclismo", grupo: "Ritmo", n_pontos: 3, disponivel: false, motivo: "Poucos treinos de ciclismo nas últimas 12 semanas" },
  { id: "geral.ctl", titulo: "Condicionamento", descricao: "Como o seu preparo evolui ao longo das semanas", modalidade: "geral", grupo: "Esforço e volume", n_pontos: 12, disponivel: true, motivo: null },
];
const DIAS_DO_PERIODO = { "12s": 84, "6m": 182, "1a": 365 };
const SEMANAS = ["jan", "fev", "mar", "abr"];
function serieFalsa(id, periodo, atleta) {
  const e = CATALOGO.find((x) => x.id === id);
  if (!e) return null;
  const volume = id.endsWith("volume_km");
  const ctl = id === "geral.ctl";
  const n = volume ? { "12s": 12, "6m": 26, "1a": 52 }[periodo] : Math.min(e.n_pontos + (periodo === "12s" ? 0 : periodo === "6m" ? 8 : 20), 40);
  const aprendendo = atleta === 31 && id === "corrida.pace.leve";
  const fim = Date.UTC(2025, 2, 20);
  const dia = 86400000;
  const passo = volume ? 7 : Math.max(2, Math.floor(DIAS_DO_PERIODO[periodo] / n));
  const base = { "corrida.pace.leve": 345, "corrida.fc.moderado": 150, "natacao.ritmo": 128 }[id] ?? 20;
  const pace = ["corrida.pace.leve", "natacao.ritmo"].includes(id);
  const txt = (v) => (pace ? `${Math.floor(v / 60)}:${String(Math.round(v % 60)).padStart(2, "0")}` : volume ? String(v.toFixed(1)).replace(".", ",") : String(Math.round(v)));
  const pontos = Array.from({ length: n }, (_, i) => {
    const t = new Date(fim - (n - 1 - i) * passo * dia);
    const iso = t.toISOString().slice(0, 10);
    const ruido = Math.sin(i * 1.7) * (pace ? 9 : 3) - (pace ? i * 0.6 : -i * 0.2);
    const v = volume ? 18 + ((i * 7) % 5) * 4 + (i === n - 1 ? -10 : 0) : ctl ? 38 + i * 0.5 : base + ruido + (i === 5 ? (pace ? 28 : 12) : 0);
    const fora = !volume && !ctl && !aprendendo && i === 5;
    const dd = iso.slice(8) + "/" + iso.slice(5, 7);
    const sem = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"][t.getUTCDay()];
    return {
      atividade_id: volume || ctl ? null : 107 + (i % 3),
      data: iso,
      data_texto: volume ? `semana de ${dd}` : `${sem} ${dd}`,
      valor: Math.round(v * 10) / 10,
      valor_texto: txt(v),
      melhor: pace && i === n - 3,
      fora_do_normal: volume || ctl || aprendendo ? null : fora,
      normal_estado: volume || ctl ? null : aprendendo ? "aprendendo" : fora ? "fora" : "dentro",
      aprendendo: aprendendo,
      parcial: volume && i === n - 1,
      rotulo: `${volume ? "Semana de" : "Treino de"} ${dd}, ${txt(v)} ${e.titulo.toLowerCase()}${fora ? ", fora do seu normal" : volume || ctl ? "" : ", dentro do seu normal"}`,
    };
  });
  const valores = pontos.map((p) => p.valor);
  const lo = volume ? 0 : Math.min(...valores) - (pace ? 10 : 4);
  const hi = Math.max(...valores) + (pace ? 10 : 4);
  const marcas = [lo, (lo + hi) / 2, hi].map((v) => ({ valor: Math.round(v * 10) / 10, rotulo: txt(v) }));
  const ref = volume || ctl || aprendendo ? null : { minimo: base - 12, maximo: base + 12, mediana: base, n: Math.min(n, 12), texto: `Seu normal ${txt(base - 12)} a ${txt(base + 12)}` };
  const ultimo = pontos.at(-1);
  return {
    atleta_id: atleta, id, titulo: e.titulo, descricao: e.descricao, modalidade: e.modalidade, grupo: e.grupo, periodo,
    inicio: new Date(fim - DIAS_DO_PERIODO[periodo] * dia).toISOString().slice(0, 10), fim: "2025-03-20",
    unidade: pace ? (id.startsWith("natacao") ? "/100 m" : "/km") : volume ? "km" : id.includes("fc") ? "bpm" : "pontos",
    versao_calculo: "evolucao_serie@1", pontos, ultimo_valor_texto: ultimo.valor_texto,
    ultimo_rotulo: volume ? "última semana completa" : `último treino, ${ultimo.data_texto}`,
    referencia: ref, aprendendo_texto: aprendendo ? "Ainda estamos aprendendo o seu normal no treino leve: faltam 3 treinos para mostrar a faixa." : null,
    eixo: { minimo: lo, maximo: hi, invertido: pace, marcas },
    frase: {
      versao: "frase_evolucao@1", tipo: "comparada", mudanca: "menor", a_favor: pace, valor_atual: base, valor_anterior: base + 12, n_atual: 3, n_anterior: 3,
      texto: pace ? `${e.titulo} nas últimas 4 semanas: ${txt(base)}${id.startsWith("natacao") ? "/100 m" : "/km"} (mediana de 3 treinos), 12 s mais rápido que nas 4 semanas anteriores (${txt(base + 12)}, 3 treinos).` : `${e.titulo} nas últimas 4 semanas: ${txt(base)} ${volume ? "km por semana" : "bpm"}, parecido com o das 4 semanas anteriores.`,
    },
  };
}

// Início v4 (#583): cartões de "Seus números" no formato da API (texto pronto, só os que têm dado). Atleta 2 não tem nenhum,
// 33 só o da melhor marca, 34 a busca responde 500.
const CARTOES = [
  { id: "esta_semana", formato: "pequeno", rotulo: "Esta semana", valor: "3 treinos", apoio: "2 h 37 min · semana passada: 4", texto: null, barras: [], destino: { tela: "evolucao", serie_id: "corrida.volume_km", atividade_id: null }, rotulo_acessivel: "Esta semana, 3 treinos, 2 horas e 37 minutos, semana passada 4 treinos. Abre a evolução do volume." },
  { id: "hoje_na_semana", formato: "pequeno", rotulo: "Hoje, sexta", valor: "Corrida leve", apoio: "da sua rotina", texto: null, barras: [], destino: { tela: "semana_padrao", serie_id: null, atividade_id: null }, rotulo_acessivel: "Hoje, sexta, corrida leve, da sua rotina. Abre a semana-padrão." },
  { id: "volume_4_semanas", formato: "largo", rotulo: "Volume das 4 semanas", valor: "30 km por semana", apoio: null, texto: "10 km a menos que nas 4 semanas anteriores.", barras: [{ data_texto: "03/02", valor_texto: "40 km", altura_pct: 100, destaque: false }, { data_texto: "10/02", valor_texto: "35 km", altura_pct: 88, destaque: false }, { data_texto: "17/02", valor_texto: "30 km", altura_pct: 75, destaque: false }, { data_texto: "24/02", valor_texto: "25 km", altura_pct: 63, destaque: true }], destino: { tela: "evolucao", serie_id: "corrida.volume_km", atividade_id: null }, rotulo_acessivel: "Volume das 4 semanas, 30 km por semana, 10 km a menos que nas 4 semanas anteriores. Abre a evolução do volume." },
  { id: "em_movimento", formato: "largo", rotulo: "Em movimento", valor: "Pace dos seus treinos leves", apoio: null, texto: "Pace dos seus treinos leves nas últimas 4 semanas: 5:42/km (mediana de 3 treinos), 12 s/km mais rápido que nas 4 anteriores (5:54/km).", barras: [], destino: { tela: "evolucao", serie_id: "corrida.pace.leve", atividade_id: null }, rotulo_acessivel: "Em movimento, pace dos seus treinos leves. Abre a evolução." },
  { id: "melhor_marca", formato: "pequeno", rotulo: "Melhor marca", valor: "21:10 · 5 km", apoio: "novo recorde · 12/03", texto: null, barras: [], destino: { tela: "treino", serie_id: null, atividade_id: 107 }, rotulo_acessivel: "Melhor marca, 21 minutos e 10 segundos nos 5 quilômetros, novo recorde em 12 de março. Abre o treino." },
];

const evolucao = {
  atleta_id: 1,
  metrica: "tiros_1km",
  periodo: null,
  reclassificacao_pendente: false,
  versao_calculo: "tiros_1km@sintetico",
  sessoes,
  unidades: { distancia: "m", duracao: "s", fc: "bpm", pace: "min/km" },
  eixos: {
    pace: {
      invertido: true,
      min_s_km: 240,
      max_s_km: 280,
      marcas: [
        { rotulo: "4:00", valor_s_km: 240 },
        { rotulo: "4:40", valor_s_km: 280 },
      ],
    },
    fc: {
      min_bpm: 150,
      max_bpm: 180,
      marcas: [
        { rotulo: "150", valor_bpm: 150 },
        { rotulo: "180", valor_bpm: 180 },
      ],
    },
  },
};
const corrida = (id) => ({
  atividade_id: id,
  modalidade: "corrida",
  subtipo: "rua",
  inicio: "2025-03-18T09:30:00Z",
  data_local: "2025-03-18",
  hora_local: "06:30",
  duracao_s: 3125,
  duracao: "0:52:05",
  distancia_m: 10000,
  distancia: "10,00 km",
  pace_medio: "5:12",
  fc_media: 152,
  clima: {
    estado: "ok",
    recente: false,
    temperatura_c: 24.3,
    temperatura_texto: "24 °C",
    sensacao_c: 25.1,
    sensacao_texto: "25 °C",
    umidade_pct: 61,
    umidade_texto: "61 %",
    vento_kmh: 8.2,
    vento_texto: "8 km/h",
    atribuicao: "Weather data by Open-Meteo.com",
  },
});

// Natação (id 106): sem pace, sem FC, distância em metros, como a API manda.
const natacao = (id) => ({
  ...corrida(id),
  modalidade: "natacao",
  subtipo: "piscina",
  inicio: "2025-03-20T10:00:00Z",
  data_local: "2025-03-20",
  hora_local: "07:00",
  duracao_s: 2700,
  duracao: "0:45:00",
  distancia_m: 1800,
  distancia: "1.800 m",
  pace_medio: null,
  fc_media: null,
  clima: { estado: "indoor", recente: false },
});
// Semana-padrão sintética (#268): segunda fartlek + natação, terça ciclismo intervalado, quarta corrida
// intervalado + natação; duas vigências. O PUT guarda em memória e devolve `atividades_reaplicadas: 0`.
const NOMES_DIA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"];
const comTexto = (itens) =>
  itens.map((i) => ({ dia_semana_texto: NOMES_DIA[i.dia_semana - 1], tipo_treino: null, ...i }));
const planoPadrao = () => [
  {
    vigente_desde: "2026-03-02",
    definido_por: "atleta",
    definido_em: "2026-03-01T21:10:00-03:00",
    itens: comTexto([
      { dia_semana: 1, modalidade: "corrida", tipo_treino: "fartlek" },
      { dia_semana: 1, modalidade: "natacao" },
      { dia_semana: 2, modalidade: "ciclismo", tipo_treino: "intervalado" },
      { dia_semana: 3, modalidade: "corrida", tipo_treino: "intervalado" },
      { dia_semana: 3, modalidade: "natacao" },
    ]),
  },
  {
    vigente_desde: "2026-02-02",
    definido_por: "professor",
    definido_em: "2026-02-01T10:00:00-03:00",
    itens: comTexto([
      { dia_semana: 2, modalidade: "corrida", tipo_treino: "leve" },
      { dia_semana: 4, modalidade: "ciclismo", tipo_treino: "longo" },
    ]),
  },
];
// Atleta de teste para forçar estados da tela da semana-padrão (entre com atleta<id>@exemplo.com); os demais ids usam o plano do atleta 1:
//   2 = sem plano (estado vazio)            3 = GET derruba a conexão (erro de rede ao carregar)
//   4 = PUT responde 422                    5 = GET responde 404 (atleta não encontrado)
//   6 = PUT derruba a conexão (erro de rede ao salvar)
const semanas = new Map();
const vigenciasDe = (id) => {
  if (!semanas.has(id)) semanas.set(id, id === 2 ? [] : planoPadrao());
  return semanas.get(id);
};
const dataLocal = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const semanaPadrao = (id, em) => {
  const dia = em ?? dataLocal(new Date());
  const ordenadas = [...vigenciasDe(id)].sort((a, b) => b.vigente_desde.localeCompare(a.vigente_desde));
  return {
    atleta_id: 1,
    em: dia,
    vigente: ordenadas.find((v) => v.vigente_desde <= dia) ?? null,
    vigencias: ordenadas.map((v) => ({ vigente_desde: v.vigente_desde, definido_por: v.definido_por, total_itens: v.itens.length })),
  };
};
const gravarSemana = (id, corpo) => {
  const nova = {
    vigente_desde: corpo.vigente_desde,
    definido_por: corpo.definido_por,
    definido_em: new Date().toISOString(),
    itens: comTexto([...corpo.itens].sort((a, b) => a.dia_semana - b.dia_semana || a.modalidade.localeCompare(b.modalidade))),
  };
  semanas.set(id, [...vigenciasDe(id).filter((v) => v.vigente_desde !== nova.vigente_desde), nova]);
  return { ...nova, atividades_reaplicadas: 0 };
};

// Check-in pós-treino sintético (#299, ADR 0012): PUT/GET/DELETE em memória, por atleta, e a lista de pendentes. Nenhum dado real.
// Atividades: 101 corrida e 106 natação sem check-in (prazo aberto); 107 corrida com check-in; 108 corrida com o prazo vencido;
// 109 parte de multiesporte com `pse_sugerida` 5; 110 treino inteiro de multiesporte (não pede check-in). Outros ids: corrida sem check-in.
// Atleta de teste para forçar estados do check-in (entre com atleta<id>@exemplo.com); os demais usam os dados acima:
//   7 = sem pendentes (lista vazia)          8 = GET dos pendentes derruba a conexão   9 = GET da atividade derruba a conexão
//  10 = PUT responde 422 genérico           11 = PUT responde 422 fora_do_prazo       12 = PUT responde 422 atividade_sem_checkin
//  13 = PUT derruba a conexão               14 = PUT responde 404                     15 = DELETE derruba a conexão
//  16 = PUT demora 4 s (estado "salvando")  17 = GET dos pendentes responde 500       18 = GET da atividade demora 6 s (carregando)
//  19 = GET da atividade responde 404 (treino não encontrado ao carregar)
// Estados do cartão Feedback por atividade (atleta 1): ver `FEEDBACK_POR_ID` abaixo.
const ANCORAS = ["repouso", "muito leve", "leve", "moderado", "um pouco difícil", "difícil", "6", "muito difícil", "8", "9", "máximo"];
const SENSACOES = ["", "Muito mal", "Mal", "Normal", "Bem", "Muito bem"];
const ATALHOS = { dor: "Dor", cansaco: "Cansaço", sono_ruim: "Sono ruim", calor: "Calor", trabalho_estresse: "Trabalho ou estresse" };
const checkins = new Map();
const chaveCheckin = (atleta, atividade) => `${atleta}:${atividade}`;
const checkinOut = (atividadeId, e) => ({
  atividade_id: atividadeId,
  pse: e.pse,
  pse_texto: ANCORAS[e.pse],
  sensacao: e.sensacao,
  sensacao_texto: SENSACOES[e.sensacao],
  nada_a_relatar: e.nada_a_relatar,
  atalhos: e.atalhos.map((chave) => ({ chave, texto: ATALHOS[chave] })),
  texto: e.texto ?? null,
  versao: "checkin@1",
  registrado_em: "2025-03-18T12:00:00Z",
  atualizado_em: "2025-03-18T12:00:00Z",
});
const iniciarCheckins = () => {
  checkins.set(chaveCheckin(1, 107), checkinOut(107, { pse: 5, sensacao: 4, nada_a_relatar: false, atalhos: ["cansaco", "trabalho_estresse"], texto: "Texto sintético de exemplo." }));
  for (const id of [111, 112, 113, 114, 115]) checkins.set(chaveCheckin(1, id), checkinOut(id, { pse: 5, sensacao: 4, nada_a_relatar: true, atalhos: [], texto: null }));
};
// Feedback sintético (#330, ADR 0013): um id por estado, sempre com texto marcador. 107 pronto (automático), 111 pronto de teste,
// 112 pendente, 113 desatualizado, 114 indisponível, 115 indisponível sem provedor; 101 e 106 sem check-in (prazo aberto), 108 sem check-in
// com o prazo vencido; 110 não elegível (`feedback: null`). Os demais ids com check-in (só o PUT cria) ficam `pendente`.
const TEXTO_FEEDBACK = "Texto de exemplo do feedback.\nSegunda linha do texto de exemplo.\nTerceira linha do texto de exemplo.";
const FEEDBACK_POR_ID = {
  107: { estado: "pronto", texto: TEXTO_FEEDBACK, origem: "automatico" },
  111: { estado: "pronto", texto: TEXTO_FEEDBACK, origem: "teste" },
  112: { estado: "pendente", mensagem: "O feedback deste treino ainda não foi gerado. Ele é preparado em lote; volte mais tarde." },
  113: { estado: "desatualizado", mensagem: "Você editou o check-in. O feedback será refeito." },
  114: { estado: "indisponivel", motivo: "provedor_erro", mensagem: "Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde." },
  115: { estado: "indisponivel", motivo: "provedor_nao_configurado", mensagem: "O feedback automático não está ligado neste app." },
};
const feedbackDe = (id, temCheckin, aberto) => {
  if (naoPedeCheckin(id)) return null;
  if (!temCheckin) {
    return {
      estado: "sem_checkin",
      mensagem: aberto ? "Faça o check-in para ver o feedback." : "O prazo do check-in deste treino acabou, então ele fica sem feedback.",
      checkin_aberto: aberto,
    };
  }
  return FEEDBACK_POR_ID[id] ?? FEEDBACK_POR_ID[112];
};
const naoPedeCheckin = (id) => id === 110;
const prazoVencido = (id) => id === 108;
const pendentesBase = [101, 106, 109];
const infoTreino = (id) => {
  const a = id === 106 ? natacao(id) : corrida(id);
  return { modalidade: id === 109 ? "ciclismo" : a.modalidade, data_local: a.data_local, hora_local: a.hora_local, duracao: a.duracao, duracao_s: a.duracao_s };
};
// Carga e forma do dia sintéticas (#466, ADR 0004 adendo 12): 106 sem FC (sem_carga), 108 aprendendo, 109 pendente e sem série, 110 sem os dois.
const cargaForma = (a) => {
  const id = a.atividade_id;
  if (id === 110) return { carga: null, forma_do_dia: null };
  const dia = a.data_local;
  const forma = { estado: "calculada", data_local: dia, ctl_texto: "41,2", atl_texto: "52,8", tsb_texto: "\u221211,6", sem_carga_no_dia: 0, texto_sem_carga: null };
  if (id === 106) {
    return { carga: { versao: "carga@2", estado: "sem_carga", motivo: "sem_fc", texto: "Este treino não tem frequência cardíaca, então não dá para estimar a carga pela FC." }, forma_do_dia: { ...forma, sem_carga_no_dia: 1, texto_sem_carga: "Há 1 treino deste dia sem carga calculada; a forma pode estar subestimada." } };
  }
  if (id === 108) {
    return { carga: { versao: "carga@2", estado: "calculada", carga: 87.43, valor_texto: "87,4", metodo: "hrtss", metodo_texto: "Estimada pela FC.", cobertura_pct: 98, texto: null }, forma_do_dia: { estado: "aprendendo", data_local: dia, sem_carga_no_dia: 0, texto_aprendendo: "Ainda aprendendo a sua forma: faltam 23 dias de histórico para estimar." } };
  }
  if (id === 109) {
    return { carga: { versao: "carga@2", estado: "pendente", texto: "A carga deste treino ainda não foi calculada." }, forma_do_dia: { estado: "sem_serie", data_local: dia, sem_carga_no_dia: 0 } };
  }
  return { carga: { versao: "carga@2", estado: "calculada", carga: 87.43, valor_texto: "87,4", metodo: "hrtss", metodo_texto: "Estimada pela FC.", cobertura_pct: 98, texto: null }, forma_do_dia: forma };
};
// Esforços e transição sintéticos (#467, ADR 0004 adendo 12). Esforços: 107 com aquecimento, quatro esforços e desaquecimento;
// 109 (ciclismo) com velocidade; 130 com 12 esforços; os demais sem. Transição: 107 sugerida pela regra, 110 (multiesporte_pai) não editável,
// o resto "sem marca". PUT e DELETE em memória (por atleta e atividade); atleta 21 = PUT dá 500, atleta 22 = PUT demora 6 s.
const transicoes = new Map();
const TRANSICAO_BASE = { 107: { valor: true, origem: "sugerido", editavel: true }, 110: { valor: false, origem: null, editavel: false } };
const chaveTransicao = (atleta, id) => `${atleta}:${id}`;
const transicaoDe = (atleta, id) => transicoes.get(chaveTransicao(atleta, id)) ?? TRANSICAO_BASE[id] ?? { valor: false, origem: null, editavel: true };
const bloco = (ordem, categoria, extra = {}) => ({
  ordem, categoria, faixa: null, faixa_rotulo: null, treino_chave: false, inicio_offset_s: ordem * 300, duracao_s: 300, distancia_m: 1000,
  parada_apos_s: null, fc_media: null, pace_s_km: null, duracao: "5:00", distancia: "1,00 km", pace: null, parada_apos: null, ...extra,
});
const esforco = (ordem, extra = {}) =>
  bloco(ordem, "esforco", { faixa: "d1000", faixa_rotulo: "1 km", fc_media: 170 + (ordem % 10), pace: `4:0${ordem % 10}`, pace_s_km: 245, ...extra });
const esforcosDe = (id) => {
  const wrap = (blocos) => ({ versao: "esforcos@1", referencia_da_atividade: false, treino_chave: false, blocos });
  if (id === 107) {
    return wrap([bloco(0, "aquecimento", { duracao: "12:10" }), esforco(1, { parada_apos: "1:00", parada_apos_s: 60 }), bloco(2, "recuperacao"), esforco(3), bloco(4, "recuperacao"), esforco(5), bloco(6, "desaquecimento", { duracao: "8:40" })]);
  }
  if (id === 109) return wrap([esforco(1, { pace: null, velocidade: "32,5", velocidade_kmh: 32.5 }), esforco(2, { pace: null, velocidade: "33,1", velocidade_kmh: 33.1 })]);
  if (id === 130) return wrap(Array.from({ length: 12 }, (_, i) => esforco(i + 1)));
  return null;
};
// Linha de base sintética `linha_base@3` (#465): 107 dentro do normal (padrão), 101 fora, 108 aprendendo e sem dado, 112 sem tipo,
// 106 natação sem métricas, 110 multiesporte (sem cartão), 109 ciclismo sem métricas.
const metricaBase = (chave, rotulo, unidade, extra) => ({ chave, rotulo, unidade, estado: "dentro", n: 6, ...extra });
const PACE_DENTRO = metricaBase("pace_medio", "Pace médio", "s/km", { valor: 312, valor_texto: "5:12 min/km", mediana: 315, mediana_texto: "5:15 min/km", desvio: -3, diferenca_texto: "3 s/km mais rápido", texto: "Mediana de 5:15 min/km, em 6 treinos leves." });
const FC_DENTRO = metricaBase("fc_media", "FC média", "bpm", { valor: 152, valor_texto: "152 bpm", mediana: 150, mediana_texto: "150 bpm", desvio: 2, diferenca_texto: "2 bpm acima", texto: "Mediana de 150 bpm, em 6 treinos leves." });
const baseLB = { versao: "linha_base@3", modalidade: "corrida", tipo_treino: "leve", janela_semanas: 12, minimo_treinos: 8 };
const semLB = (modalidade, motivo, texto) => ({ ...baseLB, modalidade, tipo_treino: null, estado: "sem_linha_base", metricas: [], motivo, texto });
const linhaBaseDe = (id) => {
  if (id === 110) return semLB("corrida", "multiesporte", "Treino de vários esportes: sem linha de base.");
  if (id === 106) return semLB("natacao", "modalidade_sem_metricas", "Ainda não há linha de base para natação.");
  if (id === 109) return semLB("ciclismo", "modalidade_sem_metricas", "Ainda não há linha de base para ciclismo.");
  if (id === 112) return semLB("corrida", "sem_tipo", "Sem linha de base: o treino não tem tipo.");
  if (id === 108) {
    return { ...baseLB, estado: "ok", metricas: [
      metricaBase("pace_medio", "Pace médio", "s/km", { estado: "aprendendo", n: 3, texto: "3 de 8 treinos do tipo leve nas últimas 12 semanas." }),
      metricaBase("fc_media", "FC média", "bpm", { estado: "sem_valor", n: 0, motivo: "sem_valor", texto: "Este treino não tem frequência cardíaca." }),
    ] };
  }
  if (id === 101) {
    return { ...baseLB, estado: "ok", metricas: [
      { ...PACE_DENTRO, estado: "fora", desvio: -25, diferenca_texto: "25 s/km mais rápido", texto: "25 s/km mais rápido que a mediana de 5:15 min/km, em 6 treinos leves." },
      { ...FC_DENTRO, estado: "fora", valor: 161, valor_texto: "161 bpm", desvio: 11, diferenca_texto: "11 bpm acima", texto: "11 bpm acima da mediana de 150 bpm, em 6 treinos leves." },
      metricaBase("carga_hora", "Carga por hora", "pontos/h", { estado: "fora", valor: 61, valor_texto: "61,0 pontos/h", mediana: 52, mediana_texto: "52,0 pontos/h", desvio: 9, diferenca_texto: "9,0 pontos/h maior", texto: "9,0 pontos/h maior que a mediana de 52,0 pontos/h, em 6 treinos leves." }),
    ] };
  }
  return { ...baseLB, estado: "ok", metricas: [PACE_DENTRO, FC_DENTRO] };
};
const comCheckin = (a, atleta) => {
  const id = a.atividade_id;
  const e = checkins.get(chaveCheckin(atleta, id)) ?? null;
  const minutos = Math.round(a.duracao_s / 60);
  const carga_pse = naoPedeCheckin(id)
    ? null
    : e
      ? { versao: "carga_pse@1", estado: "calculada", pse: e.pse, minutos, valor: e.pse * minutos, valor_texto: `${e.pse * minutos} UA`, texto: `Carga pela PSE: ${e.pse} x ${minutos} min = ${e.pse * minutos} UA.` }
      : { versao: "carga_pse@1", estado: "sem_checkin", minutos, texto: "Sem check-in: a carga pela PSE precisa da PSE do treino." };
  return {
    ...a,
    ...(id === 109 ? { modalidade: "ciclismo", subtipo: "rua", pace_medio: null } : {}),
    ...(id === 110 ? { subtipo: "multiesporte_pai" } : {}),
    checkin: e,
    carga_pse,
    checkin_aberto: e ? true : !naoPedeCheckin(id) && !prazoVencido(id),
    feedback: feedbackDe(id, !!e, !naoPedeCheckin(id) && !prazoVencido(id)),
    pse_sugerida: id === 109 && !e ? 5 : null,
    ...cargaForma(a),
    linha_base: linhaBaseDe(id),
    esforcos: esforcosDe(id),
    transicao: transicaoDe(atleta, id),
  };
};
const pendentesDe = (atleta) => {
  const ids = atleta === 7 ? [] : pendentesBase.filter((id) => !checkins.has(chaveCheckin(atleta, id)));
  const lista = ids.map((id) => {
    const t = infoTreino(id);
    const nome = { corrida: "Corrida", ciclismo: "Ciclismo", natacao: "Natação" }[t.modalidade];
    return { atividade_id: id, modalidade: t.modalidade, data_local: t.data_local, hora_local: t.hora_local, duracao: t.duracao, titulo: `${nome}, ${Math.round(t.duracao_s / 60)} min` };
  });
  return { dias: 7, total: lista.length, pendentes: lista };
};
const validarCheckin = (c) =>
  Number.isInteger(c?.pse) && c.pse >= 0 && c.pse <= 10 && Number.isInteger(c?.sensacao) && c.sensacao >= 1 && c.sensacao <= 5 &&
  Array.isArray(c?.atalhos) && c.atalhos.every((a) => a in ATALHOS) && (c.texto == null || String(c.texto).length <= 500) &&
  (c.nada_a_relatar ? c.atalhos.length === 0 && c.texto == null : c.atalhos.length > 0 || !!c.texto);
const erro422 = (type) => ({ detail: [{ loc: ["body"], msg: "sintético", type }] });
iniciarCheckins();
const atividade = (id, atleta = 1) => comCheckin(id === 106 ? natacao(id) : corrida(id), atleta);

// Caixa do dia sintética (#426, ADR 0015): `GET /professores/{id}/caixa-do-dia`. Alunos fictícios "Atleta Fixture ...", texto marcador na observação.
// Professor de teste (entre com professor<id>@exemplo.com): 1 = com conteúdo; 2 = sem alunos; 3 = ninguém com motivo e sem novos;
// 4 = derruba a conexão; 5 = 404 uniforme `professor_inexistente`; 6 = 500. Outros ids: 404 uniforme (o servidor de verdade não diz a causa).
const detalheCheckin = {
  tipo_confirmado: false,
  tipo_texto: "Intervalado",
  tipo_origem_texto: "sugerido pela regra",
  checkin: {
    pse_texto: "8",
    sensacao: 2,
    sensacao_texto: "Mal",
    atalhos: [{ chave: "dor", texto: "Dor" }, { chave: "cansaco", texto: "Cansaço" }],
    nada_a_relatar: false,
    observacao: "Texto de exemplo escrito à mão.",
  },
  feedback: { estado: "pronto", texto: "Texto de exemplo do feedback.", origem: "automatico" },
};
const detalheSemCheckin = {
  tipo_confirmado: false,
  tipo_texto: null,
  tipo_origem_texto: null,
  checkin: null,
  feedback: { estado: "sem_checkin", mensagem: "O prazo do check-in deste treino acabou, então ele fica sem feedback.", checkin_aberto: false },
};
const caixaComConteudo = {
  versao: "atencao@2",
  hoje: "2025-11-13",
  janela_atencao_dias: 7,
  janela_novos_dias: 14,
  alunos: [
    {
      atleta_id: 1, nome: "Atleta Fixture Ana", sem_motivo: false, texto_sem_motivo: null,
      treinos: [{
        atividade_id: 501, modalidade: "corrida", data_local: "2025-11-11", hora_local: "06:30", duracao_texto: "45 min",
        motivos: [
          { codigo: "dor", texto: "Treino de terça com dor marcada no check-in." },
          { codigo: "fora_do_normal", texto: "Treino de terça fora do normal: FC média acima do habitual." },
        ],
        detalhe: detalheCheckin,
      }],
    },
    {
      atleta_id: 2, nome: "Atleta Fixture Bruno", sem_motivo: false, texto_sem_motivo: null,
      treinos: [{
        atividade_id: 502, modalidade: "corrida", data_local: "2025-11-12", hora_local: "07:00", duracao_texto: "50 min",
        motivos: [{ codigo: "divergencia", texto: "Treino de quarta diferente da semana-padrão: previsto intervalado, sem esforço detectado." }],
        detalhe: { ...detalheSemCheckin, tipo_texto: "Leve", tipo_origem_texto: "confirmado por você", tipo_confirmado: true },
      }],
    },
    {
      atleta_id: 3, nome: "Atleta Fixture Carla", sem_motivo: false, texto_sem_motivo: null,
      treinos: [{
        atividade_id: 503, modalidade: "ciclismo", data_local: "2025-11-08", hora_local: "08:00", duracao_texto: "1 h 10",
        motivos: [{ codigo: "checkin_vencendo", texto: "Treino de sábado sem check-in; o prazo termina em 2 dias." }],
        detalhe: detalheSemCheckin,
      }],
    },
    { atleta_id: 4, nome: "Atleta Fixture Diego", sem_motivo: true, texto_sem_motivo: "Nada a destacar nos últimos 7 dias.", treinos: [] },
    { atleta_id: 5, nome: "Atleta Fixture Elisa", sem_motivo: true, texto_sem_motivo: "Nada a destacar nos últimos 7 dias.", treinos: [] },
  ],
  novos: [
    {
      atividade_id: 511, atleta_id: 1, atleta_nome: "Atleta Fixture Ana", modalidade: "corrida", data_local: "2025-11-11", hora_local: "06:30",
      duracao_texto: "45 min", tipo_sugerido: "intervalado", tipo_sugerido_texto: "Intervalado", origem_texto: "sugerido pela regra", detalhe: detalheCheckin,
    },
    {
      atividade_id: 512, atleta_id: 4, atleta_nome: "Atleta Fixture Diego", modalidade: "natacao", data_local: "2025-11-10", hora_local: "18:00",
      duracao_texto: "40 min", tipo_sugerido: "leve", tipo_sugerido_texto: "Leve", origem_texto: "sugerido pela semana-padrão",
      detalhe: { ...detalheSemCheckin, tipo_texto: "Leve", tipo_origem_texto: "sugerido pela semana-padrão" },
    },
  ],
};
const professorInexistente = { detail: [{ loc: ["path", "professor_id"], msg: "professor inexistente", type: "professor_inexistente" }] };
// `PUT /professores/{id}/tipos-de-treino` (#427): ids aceitos e tipos sugeridos dos treinos novos acima; o lote não é gravado.
const TIPOS_LOTE = ["leve", "moderado", "longo", "intervalado", "fartlek"];
const NOVOS_DA_CAIXA = [511, 512];
const SUGERIDO_DA_CAIXA = { 511: "intervalado", 512: "leve" };
const caixaDe = (id) => {
  if (id === 2) return { ...caixaComConteudo, alunos: [], novos: [] };
  if (id === 3) return { ...caixaComConteudo, alunos: caixaComConteudo.alunos.filter((a) => a.sem_motivo), novos: [] };
  return caixaComConteudo;
};

// Entrar, sair e trocar a senha sintéticos (#502, ADR 0016). Contas fictícias @exemplo.com, todas com a senha SENHA_SINTETICA:
//   atleta<N>@exemplo.com e professor<N>@exemplo.com (N = 1 a 30): entram como o atleta ou o professor N, e os ids de teste de cada
//   tela (ver os comentários acima: atleta 7, 8, 9... e professor 2, 3...) continuam valendo, agora pela conta e não por variável de ambiente.
//   primeiro-acesso@exemplo.com = atleta 1 com a senha provisória (a troca é obrigatória)
//   muitas@exemplo.com = sempre 429 com espere_s 300      servidor@exemplo.com = sempre 500       desativada@exemplo.com = 401 (o mesmo)
// O acesso é "token-sintetico-<papel>-<N>" (qualquer N de 1 a 40 vale, sem relógio): "token-sintetico-expirado" dá sempre 401 e
// "token-sintetico-trocar" é o atleta 1 com a troca obrigatória. As capturas (scripts/capturas.mjs) usam esses acessos sem passar pela tela.
// Sair revoga o acesso; trocar a senha revoga e devolve outro. Todas as rotas de dado pedem o Bearer (401) e o id do caminho tem de ser o da conta (404).
const SENHA_SINTETICA = "senha-sintetica-123";
const senhasTrocadas = new Map();
const revogados = new Set();
const trocaPendente = new Set(["token-sintetico-trocar"]);
const geracao = new Map();
const RE_TOKEN = /^token-sintetico-(atleta|professor)-(\d+)(?:-(?:g\d+|trocar))?$/;
const contaDoToken = (t) => {
  if (!t || revogados.has(t)) return null;
  if (t === "token-sintetico-trocar") return { papel: "atleta", id: 1 };
  const m = t.match(RE_TOKEN);
  const id = m ? Number(m[2]) : 0;
  return m && id >= 1 && id <= 40 ? { papel: m[1], id } : null;
};
const quemSou = (conta, token) => ({
  papel: conta.papel,
  atleta_id: conta.papel === "atleta" ? conta.id : null,
  professor_id: conta.papel === "professor" ? conta.id : null,
  nome: conta.papel === "atleta" ? `Atleta Fixture ${conta.id}` : `Professor Fixture ${conta.id}`,
  expira_em: "2099-12-31T23:59:59Z",
  troca_de_senha_obrigatoria: trocaPendente.has(token),
});
const lerJson = (req) =>
  new Promise((ok) => {
    let texto = "";
    req.on("data", (c) => (texto += c));
    req.on("end", () => {
      try {
        ok(JSON.parse(texto));
      } catch {
        ok(null);
      }
    });
  });
const emailDaConta = (c) => `${c.papel}${c.id}@exemplo.com`;

// Chat "Pergunte ao seu treino" (#600, ADR 0017, adendo 16): conversas sintéticas em memória, no formato da API. Gatilhos na pergunta:
// "receita" = fora do tema; "mude" = pedido de mudança; "quebrar" = estado erro; "reprovar" = reprovada; "demorar" = responde só depois de 40 s.
// Atleta 35: 429 com espere_texto; 36: 429 sem espere_texto (só o detail); 37: derruba a conexão ao perguntar; 2 não tem treinos.
const SP = new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
const emSaoPaulo = (d) => `${SP.format(d).replace(" ", "T")}-03:00`;
const ha = (minutos) => emSaoPaulo(new Date(Date.now() - minutos * 60000));
const RESPOSTAS_CHAT = {
  "como foi minha semana?": { texto: "Nesta semana você correu 3 vezes, 28,4 km no total. O treino mais longo foi de 12,1 km, no domingo. O pace dos treinos leves ficou perto do seu normal.", links: [{ tipo: "evolucao", rotulo: "Abrir na Evolução", serie_id: "corrida.volume_km" }, { tipo: "treino", rotulo: "Abrir treino", atividade_id: 107, data_texto: "qui 20/03" }] },
  "meu pace nos treinos leves melhorou?": { texto: "Sim. Nas últimas 12 semanas o seu pace nos treinos leves foi de 5:52 para 5:41 por km, e a FC média ficou parecida.", links: [{ tipo: "evolucao", rotulo: "Abrir na Evolução", serie_id: "corrida.pace.leve" }] },
  "quanto corri neste mês?": { texto: "Neste mês você correu 96,3 km em 9 treinos.", links: [{ tipo: "evolucao", rotulo: "Abrir na Evolução", serie_id: "corrida.volume_km" }] },
  "como estão minha carga e minha forma?": { texto: "Sua carga dos últimos 7 dias está um pouco acima da média das últimas semanas. A sua forma está em 4, um valor de quem está descansado o bastante.", links: [{ tipo: "evolucao", rotulo: "Abrir na Evolução", serie_id: "geral.ctl" }] },
  "o que escrevi no check-in de ontem?": { texto: "No check-in de ontem você marcou esforço 6 de 10 e escreveu: pernas pesadas no começo, melhorou depois do quarto quilômetro.", links: [{ tipo: "treino", rotulo: "Abrir treino", atividade_id: 107, data_texto: "qui 20/03" }] },
  "como foi meu último treino?": { texto: "O seu último treino foi uma rodagem de 10,2 km em 58:41, pace médio de 5:45 por km, dentro do seu normal.", links: [{ tipo: "treino", rotulo: "Abrir treino", atividade_id: 107, data_texto: "qui 20/03" }] },
};
const TEXTO_RECUSA_TEMA = "Eu respondo perguntas sobre os seus treinos. Pergunte, por exemplo, sobre o seu pace, a sua carga ou como foi a sua semana.";
const TEXTO_RECUSA_MUDANCA = "Mudar o treino é com o seu professor. Posso mostrar o que os seus treinos dizem, se isso ajudar na conversa com ele.";
const TEXTO_FALHA = "Não consegui responder agora. Tente de novo em instantes.";
const conversasChat = new Map();
let proximaConversa = 100;
let proximaMensagem = 1000;
function conversasDe(atleta) {
  if (!conversasChat.has(atleta)) {
    const msg = (ordem, pergunta, minutos) => ({ id: ++proximaMensagem, ordem, pergunta, estado: "respondida", motivo: null, ...RESPOSTAS_CHAT[pergunta.toLowerCase()], criada_em: ha(minutos) });
    const mk = (titulo, minutos, mensagens) => ({ id: ++proximaConversa, titulo, criada_em: ha(minutos + 5), atualizada_em: ha(minutos), mensagens });
    conversasChat.set(atleta, [
      mk("Como foi minha semana?", 30, [msg(1, "Como foi minha semana?", 30)]),
      mk("Meu pace nos treinos leves melhorou?", 26 * 60, [msg(1, "Meu pace nos treinos leves melhorou?", 26 * 60)]),
      mk("Quanto corri neste mês?", 5 * 24 * 60, [msg(1, "Quanto corri neste mês?", 5 * 24 * 60)]),
    ]);
  }
  return conversasChat.get(atleta);
}
function responderChat(pergunta) {
  const p = pergunta.toLowerCase();
  const base = { id: ++proximaMensagem, pergunta, links: [], criada_em: emSaoPaulo(new Date()) };
  if (p.includes("receita")) return { ...base, estado: "recusada", motivo: "fora_do_tema", texto: TEXTO_RECUSA_TEMA };
  if (p.includes("mude")) return { ...base, estado: "recusada", motivo: "pedido_de_mudanca", texto: TEXTO_RECUSA_MUDANCA };
  if (p.includes("quebrar")) return { ...base, estado: "erro", motivo: "provedor", texto: TEXTO_FALHA };
  if (p.includes("reprovar")) return { ...base, estado: "reprovada", motivo: "numero_nao_confere", texto: TEXTO_FALHA };
  const pronta = RESPOSTAS_CHAT[p.trim()];
  return { ...base, estado: "respondida", motivo: null, ...(pronta ?? { texto: "Pelo que vejo nos seus treinos, está tudo dentro do seu normal nas últimas semanas.", links: [] }) };
}
const NAO_AUTENTICADO = { detail: "não autenticado" };

// Consentimento do atleta e termo sintéticos (#503, ADR 0016 item 7): `GET /termo-de-consentimento` e, por atleta, em memória,
// `GET /atletas/{id}/professores`, `PUT` e `DELETE .../professores/{pid}/consentimento`. Professores fictícios "Exemplo": 11 e 13 aguardando
// (o 13 aceitou um termo antigo), 12 consentido. Atleta de teste (entre com atleta<id>@exemplo.com): 2 = sem vínculos; 23 = GET derruba a
// conexão; 24 = PUT responde 409 (termo mudou); 25 = PUT derruba a conexão; 26 = DELETE derruba a conexão; 27 = GET responde 500.
const TERMO_VERSAO = "termo@0-provisorio";
const TERMO = {
  versao: TERMO_VERSAO,
  provisorio: true,
  texto:
    "Termo de consentimento (provisório). Ao aceitar, você autoriza o professor indicado a ver, no aplicativo, os seus treinos, o seu check-in (esforço percebido, sensação, atalhos e a observação que você escrever) e o feedback do treino.\nO professor não vê a sua carga de treino em números, a recuperação, o clima nem a sua semana-padrão, e não vê os dados de outros atletas. Você pode revogar quando quiser: a partir daí o professor deixa de ver os seus dados, mas o que ele já confirmou no seu treino (como o tipo) continua.\nEstes são dados pessoais de saúde. Texto sintético de exemplo.",
};
const vinculosPorAtleta = new Map();
const vinculosDe = (atleta) => {
  if (!vinculosPorAtleta.has(atleta)) {
    vinculosPorAtleta.set(
      atleta,
      atleta === 2
        ? []
        : [
            { professor_id: 11, nome: "Carlos Exemplo", consentimento: false, termo_versao: null, consentimento_em: null, consentimento_revogado_em: null, termo_desatualizado: false },
            { professor_id: 12, nome: "Marina Exemplo", consentimento: true, termo_versao: TERMO_VERSAO, consentimento_em: "2026-11-10T12:00:00Z", consentimento_revogado_em: null, termo_desatualizado: false },
            { professor_id: 13, nome: "Paulo Exemplo", consentimento: false, termo_versao: "termo@antigo", consentimento_em: "2026-10-01T12:00:00Z", consentimento_revogado_em: null, termo_desatualizado: true },
          ],
    );
  }
  return vinculosPorAtleta.get(atleta);
};

// Lista de treinos sintética (#adendo 13 da ADR 0004): `GET /atletas/{id}/atividades`, mais recente primeiro, 47 treinos paginados por cursor
// (`antes_de` = o `proximo` anterior; aqui o cursor é a posição). Filtros `modalidade` e `checkin_pendente`. Atleta de teste (entre com
// atleta<id>@exemplo.com): 2 = lista vazia; 28 = responde 500; 29 = derruba a conexão; 30 = a segunda página responde 500 (erro ao carregar mais).
const TIPOS_LISTA = ["leve", "moderado", "longo", "intervalado", "fartlek", null];
const treinosSinteticos = Array.from({ length: 47 }, (_, i) => {
  const d = new Date(Date.UTC(2025, 2, 20) - i * 86400000);
  const data = d.toISOString().slice(0, 10);
  const modalidade = i % 5 === 2 ? "ciclismo" : i % 4 === 1 ? "natacao" : "corrida";
  const tipo = modalidade === "natacao" ? null : TIPOS_LISTA[i % 6];
  const minutos = 35 + ((i * 7) % 50);
  const metros = modalidade === "natacao" ? 1200 + (i % 4) * 300 : 6000 + (i % 7) * 1500;
  const nao = i % 11 === 10;
  const checkin = nao ? "nao_se_aplica" : i < 3 ? "pendente" : i === 3 ? "vencido" : "feito";
  const feedback = nao ? null : checkin === "feito" ? (i === 5 ? "desatualizado" : "pronto") : "sem_checkin";
  return {
    atividade_id: 300 + i,
    inicio: `${data}T09:30:00Z`,
    data_local: data,
    hora_local: i % 3 === 0 ? "06:30" : "18:15",
    modalidade,
    subtipo: modalidade === "natacao" ? "piscina" : "rua",
    tipo_treino: tipo,
    duracao_s: minutos * 60,
    duracao: `${Math.floor(minutos / 60)}:${String(minutos % 60).padStart(2, "0")}:00`,
    distancia_m: metros,
    distancia: modalidade === "natacao" ? `${metros.toLocaleString("pt-BR")} m` : `${(metros / 1000).toFixed(2).replace(".", ",")} km`,
    destaque: tipo === "intervalado" ? "5 x 1 km a 4:11 min/km" : null,
    checkin_estado: checkin,
    feedback_estado: feedback,
    normal_estado: [null, "dentro", "fora", "aprendendo"][i % 4],
  };
});
const listaTreinos = (atleta, q) => {
  let itens = atleta === 2 ? [] : treinosSinteticos;
  const mod = q.get("modalidade");
  if (mod) itens = itens.filter((t) => t.modalidade === mod);
  if (q.get("checkin_pendente") === "true") itens = itens.filter((t) => t.checkin_estado === "pendente");
  const limite = Math.min(Number(q.get("limite") ?? 20) || 20, 100);
  const inicio = Number(q.get("antes_de") ?? 0) || 0;
  const pagina = itens.slice(inicio, inicio + limite);
  return { atleta_id: atleta, limite, itens: pagina, proximo: inicio + limite < itens.length ? String(inicio + limite) : null };
};

createServer((req, res) => {
  const cabecalhos = {
    "content-type": "application/json",
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "authorization, content-type, accept",
    "access-control-allow-methods": "*",
  };
  if (req.method === "OPTIONS") return res.writeHead(204, cabecalhos).end();
  const { pathname, searchParams } = new URL(req.url, "http://x");
  const acesso = (req.headers.authorization ?? "").replace(/^Bearer /, "");
  const falar = (status, obj) => res.writeHead(status, cabecalhos).end(obj === undefined ? undefined : JSON.stringify(obj));
  if (pathname === "/sessao" && req.method === "POST") {
    lerJson(req).then((c) => {
      const email = String(c?.email ?? "").trim().toLowerCase();
      const senha = String(c?.senha ?? "");
      if (email === "muitas@exemplo.com") return res.writeHead(429, { ...cabecalhos, "retry-after": "300" }).end(JSON.stringify({ detail: "muitas tentativas", espere_s: 300 }));
      if (email === "servidor@exemplo.com") return falar(500, { detail: "erro sintético" });
      const m = email === "primeiro-acesso@exemplo.com" ? ["", "atleta", "1"] : email.match(/^(atleta|professor)(\d+)@exemplo\.com$/) && ["", ...email.match(/^(atleta|professor)(\d+)@/).slice(1)];
      const conta = m && Number(m[2]) >= 1 && Number(m[2]) <= 30 ? { papel: m[1], id: Number(m[2]) } : null;
      const esperada = conta ? (senhasTrocadas.get(email) ?? SENHA_SINTETICA) : null;
      if (!conta || senha !== esperada) return falar(401, { detail: "e-mail ou senha incorretos" });
      const token = email === "primeiro-acesso@exemplo.com" ? "token-sintetico-trocar" : `token-sintetico-${conta.papel}-${conta.id}`;
      revogados.delete(token);
      return falar(200, { token, ...quemSou(conta, token) });
    });
    return;
  }
  if (pathname === "/health") return falar(200, { status: "ok" });
  const sessaoDe = contaDoToken(acesso);
  if (!sessaoDe) return falar(401, NAO_AUTENTICADO);
  if (pathname === "/sessao" && req.method === "GET") return falar(200, quemSou(sessaoDe, acesso));
  if (pathname === "/sessao" && req.method === "DELETE") {
    revogados.add(acesso);
    return falar(204);
  }
  if (pathname === "/conta/senha" && req.method === "PUT") {
    lerJson(req).then((c) => {
      const email = acesso === "token-sintetico-trocar" ? "primeiro-acesso@exemplo.com" : emailDaConta(sessaoDe);
      const atual = senhasTrocadas.get(email) ?? SENHA_SINTETICA;
      const invalido = (loc, type, msg) => falar(422, { detail: [{ loc: ["body", loc], msg, type }] });
      if (c?.senha_atual !== atual) return invalido("senha_atual", "senha_atual_incorreta", "senha atual incorreta");
      if (typeof c?.senha_nova !== "string" || c.senha_nova.length < 10 || c.senha_nova === c.senha_atual) {
        return invalido("senha_nova", "senha_nova_invalida", "a senha nova precisa de pelo menos 10 caracteres e ser diferente da atual");
      }
      senhasTrocadas.set(email, c.senha_nova);
      revogados.add(acesso);
      trocaPendente.delete(acesso);
      const g = (geracao.get(email) ?? 0) + 1;
      geracao.set(email, g);
      return falar(200, { token: `token-sintetico-${sessaoDe.papel}-${sessaoDe.id}-g${g}`, expira_em: "2099-12-31T23:59:59Z" });
    });
    return;
  }
  if (trocaPendente.has(acesso)) return falar(403, { detail: [{ loc: [], msg: "troque a senha provisória", type: "troca_de_senha_obrigatoria" }] });
  // O id do caminho tem de ser o da conta; senão, o mesmo 404 de "não existe".
  const dono = pathname.match(/^\/(atletas|professores)\/(\d+)(?:\/|$)/);
  if (dono && ((dono[1] === "atletas") !== (sessaoDe.papel === "atleta") || Number(dono[2]) !== sessaoDe.id)) {
    return falar(404, dono[1] === "professores" ? professorInexistente : { detail: "não encontrado" });
  }
  if (pathname === "/termo-de-consentimento" && req.method === "GET") return falar(200, TERMO);
  const chat = pathname.match(/^\/atletas\/(\d+)\/conversas(?:\/(\d+))?(\/mensagens)?$/);
  if (chat) {
    const atleta = Number(chat[1]);
    const lista = conversasDe(atleta);
    const conversa = chat[2] ? lista.find((c) => c.id === Number(chat[2])) : null;
    const naoAchou = { detail: "não encontrado" };
    if (!chat[2] && req.method === "GET") return falar(200, { atleta_id: atleta, conversas: lista.map(({ mensagens, ...resumo }) => resumo) });
    if (chat[2] && !chat[3] && req.method === "GET") return conversa ? falar(200, conversa) : falar(404, naoAchou);
    if (chat[2] && !chat[3] && req.method === "DELETE") {
      if (!conversa) return falar(404, naoAchou);
      lista.splice(lista.indexOf(conversa), 1);
      return falar(204);
    }
    if (req.method === "POST" && (!chat[2] || chat[3])) {
      if (atleta === 37) return req.destroy();
      if (atleta === 35) return res.writeHead(429, { ...cabecalhos, "retry-after": "720" }).end(JSON.stringify({ detail: "Você fez 20 perguntas na última hora.", espere_texto: "Você pode perguntar de novo em 12 min.", espere_s: 720 }));
      if (atleta === 36) return res.writeHead(429, { ...cabecalhos, "retry-after": "720" }).end(JSON.stringify({ detail: "Você fez 20 perguntas na última hora.", espere_s: 720 }));
      lerJson(req).then((c) => {
        const pergunta = typeof c?.pergunta === "string" ? c.pergunta.trim() : "";
        if (!pergunta || pergunta.length > 1000) return falar(422, { detail: [{ loc: ["body", "pergunta"], msg: "pergunta inválida", type: "string_too_short" }] });
        if (chat[2] && !conversa) return falar(404, naoAchou);
        const demora = pergunta.toLowerCase().includes("demorar") ? 40000 : 0;
        setTimeout(() => {
          const m = responderChat(pergunta);
          if (conversa) {
            m.ordem = conversa.mensagens.length + 1;
            conversa.mensagens.push(m);
            conversa.atualizada_em = m.criada_em;
            return falar(200, m);
          }
          m.ordem = 1;
          const nova = { id: ++proximaConversa, titulo: pergunta.slice(0, 80), criada_em: m.criada_em, atualizada_em: m.criada_em, mensagens: [m] };
          lista.unshift(nova);
          falar(201, nova);
        }, demora);
      });
      return;
    }
  }
  const co = pathname.match(/^\/atletas\/(\d+)\/professores(?:\/(\d+)\/consentimento)?$/);
  if (co) {
    const atleta = Number(co[1]);
    const lista = vinculosDe(atleta);
    if (!co[2] && req.method === "GET") {
      if (atleta === 23) return req.destroy();
      if (atleta === 27) return falar(500, { detail: "erro sintético" });
      return falar(200, { atleta_id: atleta, termo_vigente: TERMO_VERSAO, professores: lista });
    }
    const v = lista.find((x) => x.professor_id === Number(co[2]));
    if (co[2] && req.method === "PUT") {
      if (atleta === 25) return req.destroy();
      lerJson(req).then((c) => {
        if (!v) return falar(404, { detail: "vínculo não encontrado" });
        if (atleta === 24 || c?.termo_versao !== TERMO_VERSAO) return falar(409, { detail: "o termo mudou: leia a versão atual" });
        Object.assign(v, { consentimento: true, termo_versao: TERMO_VERSAO, consentimento_em: new Date().toISOString(), consentimento_revogado_em: null, termo_desatualizado: false });
        falar(200, v);
      });
      return;
    }
    if (co[2] && req.method === "DELETE") {
      if (atleta === 26) return req.destroy();
      if (!v) return falar(404, { detail: "vínculo não encontrado" });
      Object.assign(v, { consentimento: false, consentimento_revogado_em: new Date().toISOString() });
      return falar(204);
    }
  }
  const lt = pathname.match(/^\/atletas\/(\d+)\/atividades$/);
  if (lt && req.method === "GET") {
    const atleta = Number(lt[1]);
    if (atleta === 29) return req.destroy();
    if (atleta === 28 || (atleta === 30 && searchParams.get("antes_de"))) return falar(500, { detail: "erro sintético" });
    return falar(200, listaTreinos(atleta, searchParams));
  }
  let corpo = null;
  const tp = pathname.match(/^\/professores\/(\d+)\/tipos-de-treino$/);
  if (tp && req.method === "PUT") {
    const id = Number(tp[1]);
    let texto = "";
    req.on("data", (c) => (texto += c));
    req.on("end", () => {
      if (id > 6 || id === 5) return res.writeHead(404, cabecalhos).end(JSON.stringify(professorInexistente));
      if (id === 4) return req.destroy();
      if (id === 6) return res.writeHead(500, cabecalhos).end(JSON.stringify({ detail: "erro sintético" }));
      let itens;
      try {
        itens = JSON.parse(texto);
      } catch {
        itens = null;
      }
      const ids = Array.isArray(itens) ? itens.map((i) => i?.atividade_id) : [];
      const tiposOk = Array.isArray(itens) && itens.every((i) => TIPOS_LOTE.includes(i?.tipo_treino));
      if (!Array.isArray(itens) || itens.length < 1 || itens.length > 200 || new Set(ids).size !== ids.length || !tiposOk) {
        return res.writeHead(422, cabecalhos).end(JSON.stringify(erro422("value_error")));
      }
      if (ids.some((i) => !NOVOS_DA_CAIXA.includes(i))) return res.writeHead(404, cabecalhos).end(JSON.stringify({ detail: [{ loc: ["body"], msg: "atividade não encontrada", type: "atividade_nao_encontrada" }] }));
      // Não grava nada: a API falsa devolve só as contagens (confirmar = tipo igual ao sugerido; corrigir = diferente).
      const confirmados = itens.filter((i) => i.tipo_treino === SUGERIDO_DA_CAIXA[i.atividade_id]).length;
      res.writeHead(200, cabecalhos).end(JSON.stringify({ confirmados, corrigidos: itens.length - confirmados }));
    });
    return;
  }
  const cx = pathname.match(/^\/professores\/(\d+)\/caixa-do-dia$/);
  if (cx) {
    const id = Number(cx[1]);
    if (id === 4) return req.destroy();
    if (id === 6) return res.writeHead(500, cabecalhos).end(JSON.stringify({ detail: "erro sintético" }));
    if (id > 6) return res.writeHead(404, cabecalhos).end(JSON.stringify(professorInexistente));
    if (id === 5) return res.writeHead(404, cabecalhos).end(JSON.stringify(professorInexistente));
    return res.writeHead(200, cabecalhos).end(JSON.stringify(caixaDe(id)));
  }
  const sp = pathname.match(/^\/atletas\/(\d+)\/semana-padrao$/);
  if (sp) {
    const id = Number(sp[1]);
    if (req.method === "PUT") {
      if (id === 6) return req.destroy();
      let texto = "";
      req.on("data", (c) => (texto += c));
      req.on("end", () => {
        if (id === 4) return res.writeHead(422, cabecalhos).end(JSON.stringify({ detail: [{ loc: ["body", "itens"], msg: "sintético", type: "value_error" }] }));
        res.writeHead(200, cabecalhos).end(JSON.stringify(gravarSemana(id, JSON.parse(texto))));
      });
      return;
    }
    if (id === 3) return req.destroy();
    if (id === 5) return res.writeHead(404, cabecalhos).end(JSON.stringify({ detail: "atleta não encontrado" }));
    return res.writeHead(200, cabecalhos).end(JSON.stringify(semanaPadrao(id, searchParams.get("em"))));
  }
  const tr = pathname.match(/^\/atletas\/(\d+)\/atividades\/(\d+)\/transicao$/);
  if (tr && (req.method === "PUT" || req.method === "DELETE")) {
    const atleta = Number(tr[1]);
    const id = Number(tr[2]);
    let texto = "";
    req.on("data", (c) => (texto += c));
    req.on("end", () => {
      if (atleta === 21) return res.writeHead(500, cabecalhos).end(JSON.stringify({ detail: "erro sintético" }));
      const responder = () => {
        const chave = chaveTransicao(atleta, id);
        if (req.method === "DELETE") transicoes.delete(chave);
        else {
          let corpoIn;
          try {
            corpoIn = JSON.parse(texto);
          } catch {
            corpoIn = null;
          }
          if (typeof corpoIn?.transicao !== "boolean") return res.writeHead(422, cabecalhos).end(JSON.stringify(erro422("value_error")));
          transicoes.set(chave, { valor: corpoIn.transicao, origem: "atleta", editavel: transicaoDe(atleta, id).editavel });
        }
        res.writeHead(200, cabecalhos).end(JSON.stringify(transicaoDe(atleta, id)));
      };
      return atleta === 22 ? void setTimeout(responder, 6000) : responder();
    });
    return;
  }
  const ck = pathname.match(/^\/atletas\/(\d+)\/atividades\/(\d+)\/checkin$/);
  if (ck) {
    const atleta = Number(ck[1]);
    const id = Number(ck[2]);
    const chave = chaveCheckin(atleta, id);
    if (req.method === "DELETE") {
      if (atleta === 15) return req.destroy();
      checkins.delete(chave);
      return res.writeHead(204, cabecalhos).end();
    }
    if (req.method === "PUT") {
      if (atleta === 13) return req.destroy();
      let texto = "";
      req.on("data", (c) => (texto += c));
      req.on("end", () => {
        const responder = () => {
          if (atleta === 14) return res.writeHead(404, cabecalhos).end(JSON.stringify({ detail: "atividade não encontrada" }));
          if (atleta === 11 || prazoVencido(id) && !checkins.has(chave)) return res.writeHead(422, cabecalhos).end(JSON.stringify(erro422("fora_do_prazo")));
          if (atleta === 12 || naoPedeCheckin(id)) return res.writeHead(422, cabecalhos).end(JSON.stringify(erro422("atividade_sem_checkin")));
          let corpoEnviado;
          try {
            corpoEnviado = JSON.parse(texto);
          } catch {
            corpoEnviado = null;
          }
          if (atleta === 10 || !validarCheckin(corpoEnviado)) return res.writeHead(422, cabecalhos).end(JSON.stringify(erro422("value_error")));
          const gravado = checkinOut(id, corpoEnviado);
          checkins.set(chave, gravado);
          res.writeHead(200, cabecalhos).end(JSON.stringify(gravado));
        };
        if (atleta === 16) setTimeout(responder, 4000);
        else responder();
      });
      return;
    }
    const existente = checkins.get(chave);
    return res.writeHead(existente ? 200 : 404, cabecalhos).end(JSON.stringify(existente ?? { detail: "check-in não encontrado" }));
  }
  const pe = pathname.match(/^\/atletas\/(\d+)\/checkins\/pendentes$/);
  if (pe) {
    const atleta = Number(pe[1]);
    if (atleta === 8) return req.destroy();
    if (atleta === 17) return res.writeHead(500, cabecalhos).end(JSON.stringify({ detail: "erro sintético" }));
    return res.writeHead(200, cabecalhos).end(JSON.stringify(pendentesDe(atleta)));
  }
  // Quinzena sintética do início v3: `GET /atletas/{id}/carga?ultimos=14` (serie_carga@2 e frase_forma@1). Atleta 21: aprendendo; 22: erro 500.
  const cg = pathname.match(/^\/atletas\/(\d+)\/carga$/);
  if (cg) {
    const atleta = Number(cg[1]);
    if (atleta === 22) return res.writeHead(500, cabecalhos).end(JSON.stringify({ detail: "erro sintético" }));
    const aprendendo = atleta === 21;
    const dias = Array.from({ length: 14 }, (_, i) => {
      const ctl = Math.round(38 + i * 0.45);
      const atl = Math.round(48 + Math.sin(i / 2) * 9 + i * 0.6);
      return { data: `2025-03-${String(7 + i).padStart(2, "0")}`, ctl, atl, tsb: ctl - atl, carga: 0, atividades: 0, calculadas: 0, sem_carga: 0, aprendendo, ctl_texto: String(ctl), atl_texto: String(atl) };
    });
    const frase = aprendendo
      ? { tipo: "aprendendo", tendencia: null, texto: "Ainda estamos aprendendo o seu ritmo: faltam alguns dias de treino para comparar.", versao: "frase_forma@1" }
      : { tipo: "acima", tendencia: "subiu", texto: "Sua fadiga está acima do seu condicionamento. É um retrato do que você treinou, não uma recomendação.", versao: "frase_forma@1" };
    return res.writeHead(200, cabecalhos).end(JSON.stringify({ atleta_id: atleta, aviso: null, dias, frase_forma: frase, periodo: { inicio: "2025-03-07", fim: "2025-03-20" }, totais: { atividades_importadas: 5, calculadas: 5, ignoradas_multiesporte: 0, pendentes: 0, por_motivo: {}, sem_carga_total: 0 }, versao: "serie_carga@2", versao_carga: "carga@2" }));
  }
  const cart = pathname.match(/^\/atletas\/(\d+)\/inicio\/cartoes$/);
  if (cart) {
    const atleta = Number(cart[1]);
    if (atleta === 34) return res.writeHead(500, cabecalhos).end(JSON.stringify({ detail: "erro sintético" }));
    const lista = atleta === 2 ? [] : atleta === 33 ? CARTOES.filter((c) => c.id === "melhor_marca") : CARTOES;
    return res.writeHead(200, cabecalhos).end(JSON.stringify({ atleta_id: atleta, data: "2025-03-21", cartoes: lista }));
  }
  const ser = pathname.match(/^\/atletas\/(\d+)\/evolucao\/series(?:\/([^/]+))?$/);
  if (ser) {
    const atleta = Number(ser[1]);
    if (atleta === 29) return req.destroy();
    if (atleta === 2) return res.writeHead(200, cabecalhos).end(JSON.stringify({ atleta_id: atleta, series: [], serie_padrao: null }));
    if (!ser[2]) {
      const series = CATALOGO.map((c) => ({ ...c, n_pontos: atleta === 31 && c.id === "corrida.pace.leve" ? 5 : c.n_pontos }));
      return res.writeHead(200, cabecalhos).end(JSON.stringify({ atleta_id: atleta, series, serie_padrao: "corrida.pace.leve" }));
    }
    const periodo = searchParams.get("periodo") ?? "12s";
    const serie = serieFalsa(decodeURIComponent(ser[2]), periodo, atleta);
    if (atleta === 32) return res.writeHead(500, cabecalhos).end(JSON.stringify({ detail: "erro" }));
    return res.writeHead(serie ? 200 : 404, cabecalhos).end(JSON.stringify(serie ?? { detail: "série não encontrada" }));
  }
  if (/^\/atletas\/\d+\/evolucao\/tiros-1km$/.test(pathname)) corpo = evolucao;
  const m = pathname.match(/^\/atletas\/(\d+)\/atividades\/(\d+)$/);
  if (m) {
    const atleta = Number(m[1]);
    if (atleta === 9) return req.destroy();
    if (atleta === 19) return res.writeHead(404, cabecalhos).end(JSON.stringify({ detail: "atividade não encontrada" }));
    const enviar = () => res.writeHead(200, cabecalhos).end(JSON.stringify(atividade(Number(m[2]), atleta)));
    return atleta === 18 ? void setTimeout(enviar, 6000) : enviar();
  }
  res.writeHead(corpo ? 200 : 404, cabecalhos).end(JSON.stringify(corpo ?? { detail: "não encontrado" }));
}).listen(porta, () => console.log(`API falsa (dados sintéticos) em http://localhost:${porta}`));
