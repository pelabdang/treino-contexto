import App from "../App";

describe("App", () => {
  it("exporta o componente raiz", () => {
    expect(typeof App).toBe("function");
  });
});
