import { lerConfig } from "../src/config";

describe("configuração", () => {
  it("usa os padrões quando as variáveis faltam", () => {
    expect(lerConfig(undefined, undefined, undefined)).toEqual({
      apiUrl: "http://localhost:8000",
      atletaId: 1,
      professorId: null,
    });
  });

  it("usa os padrões quando os valores são vazios ou inválidos", () => {
    expect(lerConfig("  ", "abc")).toEqual({ apiUrl: "http://localhost:8000", atletaId: 1, professorId: null });
    expect(lerConfig("", "0").atletaId).toBe(1);
  });

  it("lê os valores informados e tira a barra final da URL", () => {
    expect(lerConfig("http://api.local:9000/", "7", "3")).toEqual({
      apiUrl: "http://api.local:9000",
      atletaId: 7,
      professorId: 3,
    });
  });

  it("professor do piloto: vazio, zero, negativo ou texto viram null (sem padrão)", () => {
    for (const v of [undefined, "", "  ", "0", "-1", "abc", "1.5"]) expect(lerConfig(undefined, undefined, v).professorId).toBeNull();
  });
});
