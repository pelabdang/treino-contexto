import { lerConfig } from "../src/config";

describe("configuração", () => {
  it("usa o padrão quando a variável falta, é vazia ou só espaços", () => {
    expect(lerConfig(undefined)).toEqual({ apiUrl: "http://localhost:8000" });
    expect(lerConfig("  ")).toEqual({ apiUrl: "http://localhost:8000" });
  });

  it("lê a URL informada e tira a barra final", () => {
    expect(lerConfig("http://api.local:9000/")).toEqual({ apiUrl: "http://api.local:9000" });
  });

  it("não carrega mais atleta nem professor (vêm da sessão)", () => {
    expect(Object.keys(lerConfig("http://api.local"))).toEqual(["apiUrl"]);
  });
});
