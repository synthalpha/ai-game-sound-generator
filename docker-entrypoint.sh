#!/bin/sh
# Docker エントリーポイントスクリプト
set -e

if [ "$SERVICE_TYPE" = "web" ]; then
    # FastAPI Webアプリケーションを起動
    UVICORN_OPTS="--host 0.0.0.0 --port 8001"
    
    if [ "$DOCKER_ENV" = "development" ]; then
        echo "Starting FastAPI Web in development mode with hot reload..."
        UVICORN_OPTS="$UVICORN_OPTS --reload"
    else
        echo "Starting FastAPI Web in production mode..."
    fi
    
    exec uvicorn src.app.web_app:app $UVICORN_OPTS
else
    # FastAPI APIを起動
    UVICORN_OPTS="--host 0.0.0.0 --port 8000"
    
    if [ "$DOCKER_ENV" = "development" ]; then
        echo "Starting FastAPI API in development mode with hot reload..."
        UVICORN_OPTS="$UVICORN_OPTS --reload"
    else
        echo "Starting FastAPI API in production mode..."
    fi
    
    exec uvicorn src.main:app $UVICORN_OPTS
fi