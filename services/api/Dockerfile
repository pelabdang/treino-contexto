# Imagem unica da API e do worker (issue #504, ADR 0016, item 10). O contexto do build e a RAIZ do repositorio:
#
#   docker build -f services/api/Dockerfile -t treino-api .
#
# A mesma imagem roda a API (comando padrao), a migracao (`alembic upgrade head`, em services/api) e os comandos do worker
# (`python -m worker.<comando>`): o App Platform sobrescreve o comando de cada componente (ver `.do/app.yaml`).
# Sem segredo na imagem: URL do banco e o resto vem do ambiente do servico. Roda sem root. Sem chave de LLM (feedback desligado, item 13).
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /usr/local/bin/uv
WORKDIR /app

# 1) dependencias (camada de cache): so os manifestos
COPY pyproject.toml uv.lock .python-version ./
COPY services/api/pyproject.toml services/api/pyproject.toml
COPY services/worker/pyproject.toml services/worker/pyproject.toml
RUN uv sync --frozen --no-dev --no-install-workspace --all-packages

# 2) codigo (sem testes nem dado: ver .dockerignore)
COPY services/api services/api
COPY services/worker services/worker
RUN uv sync --frozen --no-dev --all-packages

RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/dados-upload/fit && chown -R app:app /app/dados-upload
USER app

ENV PORT=8080 AMBIENTE=producao FIT_DIR=/app/dados-upload/fit MPLCONFIGDIR=/tmp/matplotlib
EXPOSE 8080
# `--no-access-log`: o log de acesso do uvicorn grava a query string; o middleware da API escreve a linha sem ela (app/operacao.py).
# `--proxy-headers`: atras do proxy do provedor (HTTPS termina la).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-access-log --proxy-headers --forwarded-allow-ips='*'"]
