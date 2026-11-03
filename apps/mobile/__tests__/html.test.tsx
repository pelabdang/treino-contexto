import Raiz from "../src/app/+html";

describe("HTML raiz da web", () => {
  it("declara lang pt-BR para o Chrome não oferecer tradução", () => {
    const raiz = Raiz({ children: null });
    expect(raiz.type).toBe("html");
    expect(raiz.props.lang).toBe("pt-BR");
  });
});
