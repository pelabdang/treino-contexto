import { ScrollViewStyleReset, useServerDocumentContext } from "expo-router/html";
import type { PropsWithChildren } from "react";

// HTML raiz da web. Declara pt-BR para o Chrome não oferecer tradução
// (o tradutor mudava as mensagens do app: #96, #98).
//
// Obrigatório (#218): no Expo Router 58 o export e o servidor de dev entregam o
// <script> do bundle, o CSS e a fonte por `useServerDocumentContext()` (headNodes e
// bodyNodes). Um +html que não renderiza esses nós gera uma página sem o bundle:
// fica só o fundo "carregando-fonte". Não remova {headNodes} nem {bodyNodes}.
export default function Raiz({ children }: PropsWithChildren) {
  const { htmlAttributes, bodyAttributes, headNodes, bodyNodes } = useServerDocumentContext();
  return (
    <html lang="pt-BR" {...htmlAttributes}>
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
        <ScrollViewStyleReset />
        {headNodes}
      </head>
      <body {...bodyAttributes}>
        {children}
        {bodyNodes}
      </body>
    </html>
  );
}
