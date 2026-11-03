import { lerConfig } from "../src/config";

describe("configuração", () => {
  it("usa os padrões quando as variáveis faltam", () => {
    expect(lerConfig(undefined, undefined)).toEqual({
      apiUrl: "http://localhost:8000",
      atletaId: 1,
    });
  });

  it("usa os padrões quando os valores são vazios ou inválidos", () => {
    expect(lerConfig("  ", "abc")).toEqual({ apiUrl: "http://localhost:8000", atletaId: 1 });
    expect(lerConfig("", "0").atletaId).toBe(1);
  });

  it("lê os valores informados e tira a barra final da URL", () => {
    expect(lerConfig("http://api.local:9000/", "7")).toEqual({
      apiUrl: "http://api.local:9000",
      atletaId: 7,
    });
  });
});
