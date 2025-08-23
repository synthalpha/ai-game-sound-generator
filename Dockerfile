# ベースイメージ
FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./

# ビルド引数で環境を指定（デフォルトは本番）
ARG BUILD_ENV=production

RUN if [ "$BUILD_ENV" = "development" ]; then \
        apt-get update && apt-get install -y git make && \
        apt-get clean && rm -rf /var/lib/apt/lists/* && \
        uv sync --frozen; \
    else \
        uv sync --frozen --no-dev; \
    fi

COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

# 本番環境の場合は非rootユーザー作成
RUN if [ "$BUILD_ENV" = "production" ]; then \
        useradd -m -u 1000 appuser && \
        chown -R appuser:appuser /app; \
    fi

EXPOSE 8000 8501

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# デフォルトコマンド
CMD ["/usr/local/bin/docker-entrypoint.sh"]