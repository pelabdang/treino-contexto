// API falsa com dados 100% sintéticos, só para abrir o app na web e tirar capturas
// sem backend e sem trocar config (#218). Uso: node scripts/api-falsa.mjs [porta]
// Depois: EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start --web
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
    temperatura_c: 24.3,
    sensacao_c: 25.1,
    umidade_pct: 61,
    vento_kmh: 8.2,
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
  clima: { estado: "indoor" },
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
// Atleta de teste para forçar estados da tela da semana-padrão (EXPO_PUBLIC_ATLETA_ID=<id>); os demais ids usam o plano do atleta 1:
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
// Atleta de teste para forçar estados do check-in (EXPO_PUBLIC_ATLETA_ID=<id>); os demais usam os dados acima:
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
  112: { estado: "pendente", mensagem: "O feedback deste treino ainda não foi gerado. Toque em Atualizar para ver se já está pronto." },
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

createServer((req, res) => {
  const cabecalhos = {
    "content-type": "application/json",
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "*",
    "access-control-allow-methods": "*",
  };
  if (req.method === "OPTIONS") return res.writeHead(204, cabecalhos).end();
  const { pathname, searchParams } = new URL(req.url, "http://x");
  let corpo = null;
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
