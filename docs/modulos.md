---
tipo: mapa
status: em-uso
dono: nina
atualizado: 2026-11-03
---
# Módulos

Uma nota por módulo em `docs/modulos/`. Mapa geral em [[00-inicio]].

- [[modulos/api]]: API FastAPI, modelo de dados e a evolução dos tiros de 1 km.
- [[modulos/api-client]]: pacote TypeScript `@treino/api-client`, tipos gerados do OpenAPI e função de leitura usada pelo app.
- [[modulos/banco]]: atleta, atividades e segmentos (modelo mínimo da Meta 1) e migrações.
- [[modulos/worker]]: importação da exportação Garmin, gráfico dos tiros e reclassificação.
- [[modulos/ingestao-garmin]]: leitura da exportação do Garmin Connect (JSON e FIT) em atividades e voltas.
- [[modulos/grafico-tiros]]: PNG e CSV da evolução dos tiros de 1 km.
- [[modulos/mobile]]: app React Native com Expo (iOS, Android e web).
- [[modulos/infra]]: Docker Compose, variáveis de ambiente e CI.
