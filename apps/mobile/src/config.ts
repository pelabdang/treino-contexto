// Única leitura das variáveis de ambiente do app. O Expo troca
// `process.env.EXPO_PUBLIC_*` pelo valor na hora do bundle, então o acesso
// precisa ser direto (sem desestruturar process.env).
export const API_URL_PADRAO = "http://localhost:8000";
export const ATLETA_ID_PADRAO = 1;

export type Config = {
  apiUrl: string;
  atletaId: number;
  /** Professor do piloto (caixa do dia). `null` quando a variável falta ou é inválida: sem padrão, a tela não chama a API. */
  professorId: number | null;
};

export function lerConfig(
  apiUrl: string | undefined = process.env.EXPO_PUBLIC_API_URL,
  atletaId: string | undefined = process.env.EXPO_PUBLIC_ATLETA_ID,
  professorId: string | undefined = process.env.EXPO_PUBLIC_PROFESSOR_ID,
): Config {
  const id = Number(atletaId);
  const prof = Number(professorId);
  return {
    professorId: professorId?.trim() && Number.isInteger(prof) && prof > 0 ? prof : null,
    apiUrl: apiUrl?.trim() ? apiUrl.trim().replace(/\/+$/, "") : API_URL_PADRAO,
    atletaId: atletaId?.trim() && Number.isInteger(id) && id > 0 ? id : ATLETA_ID_PADRAO,
  };
}

export const config: Config = lerConfig();
