#!/bin/sh
# Docker エントリーポイントスクリプト
set -e

if [ "$SERVICE_TYPE" = "streamlit" ]; then
    echo "Starting Streamlit UI..."
    exec streamlit run src/app/main.py \
        --server.port 8501 \
        --server.address 0.0.0.0
else
    # FastAPI APIを起動
    UVICORN_OPTS="--host 0.0.0.0 --port 8000"
    
    if [ "$DOCKER_ENV" = "development" ]; then
        echo "Starting FastAPI in development mode with hot reload..."
        UVICORN_OPTS="$UVICORN_OPTS --reload"
    else
        echo "Starting FastAPI in production mode..."
    fi
    
    exec uvicorn src.main:app $UVICORN_OPTS
fi