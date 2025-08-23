#!/bin/sh
# Docker エントリーポイントスクリプト

if [ "$SERVICE_TYPE" = "streamlit" ]; then
    # Streamlit UIを起動
    exec streamlit run src/app/main.py \
        --server.port 8501 \
        --server.address 0.0.0.0
else
    # FastAPI APIを起動
    exec uvicorn src.main:app \
        --host 0.0.0.0 \
        --port 8000
fi