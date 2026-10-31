---
tipo: modulo
status: em-uso
dono: rafa
atualizado: 2026-10-31
links: [[modulos/api]], [[produto/roadmap]]
---
# Módulo: mobile

## Para que serve
App em React Native com Expo (TypeScript) para iOS, Android e web. Hoje é um app vazio com teste de fumaça.

## Entradas e saídas
- Futuro: consome a [[modulos/api]] por cliente TypeScript gerado do OpenAPI (`packages/api-client/`).

## Arquivos principais
- `apps/mobile/App.tsx` e `apps/mobile/index.ts`
- `apps/mobile/__tests__/App.test.tsx`
- `apps/mobile/package.json` (Jest via `jest-expo`)

## Depende de
- [[modulos/api]] (ainda sem chamadas).

## Como testar
`npm test --prefix apps/mobile`. Rodar: `npx expo start`.

## Pendências
- Telas e navegação (Expo Router) nas próximas metas. Ver [[produto/roadmap]].
