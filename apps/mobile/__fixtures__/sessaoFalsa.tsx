// Sessão sintética para os testes das rotas e das telas: dá a quem renderiza o contexto de quem está dentro, sem API nem armazenamento.
import type { ReactNode } from "react";

import { ContextoSessao, type EstadoSessao, type SessaoContexto } from "../src/sessao/SessaoProvider";

export const API_TESTE = "http://api.teste";

export const dentroAtleta = (atletaId = 1): EstadoSessao => ({
  tipo: "dentro",
  papel: "atleta",
  atletaId,
  professorId: null,
  nome: "Atleta Fixture 1",
  trocaObrigatoria: false,
});

export const dentroProfessor = (professorId = 1): EstadoSessao => ({
  tipo: "dentro",
  papel: "professor",
  atletaId: null,
  professorId,
  nome: "Professor Fixture 1",
  trocaObrigatoria: false,
});

export function criarSessaoFalsa(estado: EstadoSessao = dentroAtleta(), extra: Partial<SessaoContexto> = {}): SessaoContexto {
  return {
    estado,
    apiUrl: API_TESTE,
    fetch: ((...a: Parameters<typeof fetch>) => globalThis.fetch(...a)) as typeof fetch,
    entrar: jest.fn(),
    sair: jest.fn(),
    trocarSenha: jest.fn(),
    verificarDeNovo: jest.fn(),
    registrarCaminho: jest.fn(),
    lembrarDestino: jest.fn(),
    consumirDestino: jest.fn(async () => null),
    ...extra,
  };
}

export function ComSessao({ children, sessao = criarSessaoFalsa() }: { children: ReactNode; sessao?: SessaoContexto }) {
  return <ContextoSessao.Provider value={sessao}>{children}</ContextoSessao.Provider>;
}
