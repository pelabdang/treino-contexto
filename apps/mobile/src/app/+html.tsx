import { ScrollViewStyleReset } from "expo-router/html";
import type { PropsWithChildren } from "react";

// HTML raiz da web. Declara pt-BR para o Chrome não oferecer tradução
// (o tradutor mudava as mensagens do app: #96, #98).
export default function Raiz({ children }: PropsWithChildren) {
  return (
    <html lang="pt-BR">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
        <ScrollViewStyleReset />
      </head>
      <body>{children}</body>
    </html>
  );
}
