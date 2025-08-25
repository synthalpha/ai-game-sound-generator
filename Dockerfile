# ベースイメージ
FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml uv.lock ./

# ビルド引数で環境を指定
ARG BUILD_ENV=development

# 共通パッケージをインストール
RUN apt-get update && apt-get install -y \
    git \
    make \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 開発環境の場合のみデバッグツールを追加インストール
RUN if [ "$BUILD_ENV" = "development" ]; then \
    apt-get update && apt-get install -y \
    vim \
    less \
    procps \
    net-tools \
    lsof \
    && apt-get clean && rm -rf /var/lib/apt/lists/*; \
    fi


RUN if [ "$BUILD_ENV" = "development" ]; then \
    uv sync --frozen --all-extras; \
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

# エントリーポイントを設定
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]