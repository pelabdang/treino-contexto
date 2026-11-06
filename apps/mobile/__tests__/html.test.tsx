import type { ReactElement } from "react";

import Raiz from "../src/app/+html";

jest.mock("expo-router/html", () => ({
  ScrollViewStyleReset: () => null,
  useServerDocumentContext: jest.fn(),
}));

const { useServerDocumentContext } = jest.requireMock("expo-router/html");

function filhos(el: ReactElement): ReactElement[] {
  return ([] as ReactElement[]).concat((el.props as { children?: ReactElement[] }).children ?? []);
}

describe("HTML raiz da web", () => {
  it("declara lang pt-BR para o Chrome não oferecer tradução", () => {
    useServerDocumentContext.mockReturnValue({});
    const raiz = Raiz({ children: null }) as ReactElement<{ lang: string }>;
    expect(raiz.type).toBe("html");
    expect(raiz.props.lang).toBe("pt-BR");
  });

  it("renderiza os nós do servidor: o <script> do bundle precisa chegar ao HTML (#218)", () => {
    const headNodes = <link rel="stylesheet" href="/estilo.css" />;
    const bodyNodes = <script src="/_expo/static/js/web/entry.js" defer />;
    useServerDocumentContext.mockReturnValue({ headNodes, bodyNodes });
    const raiz = Raiz({ children: <div id="root" /> }) as ReactElement;
    const [head, body] = filhos(raiz);
    expect(filhos(head)).toContain(headNodes);
    const noBody = filhos(body);
    expect(noBody).toContain(bodyNodes);
    expect(noBody.indexOf(bodyNodes)).toBeGreaterThan(0); // depois do conteúdo
  });
});
