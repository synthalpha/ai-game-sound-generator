"""FastAPI アプリケーションエントリーポイント"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Game Sound Generator API",
    description="ゲーム音楽生成API",
    version="0.1.0",
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "AI Game Sound Generator API", "status": "running"}


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}


@app.get("/api/v1/status")
async def status():
    """ステータス確認エンドポイント"""
    return {"service": "AI Game Sound Generator", "version": "0.1.0", "status": "operational"}
