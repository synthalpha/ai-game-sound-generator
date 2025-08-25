"""
FastAPIベースのWebアプリケーション。

モダンなUI/UXを提供するWebインターフェース。
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.adapters.controllers.audio_generation.api import router as api_router

# FastAPIアプリケーション初期化
app = FastAPI(
    title="AI Game Sound Generator",
    description="Tokyo Game Show 2025 Demo",
    version="1.0.0",
)

# テンプレートとスタティックファイルの設定
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# 静的ファイルのマウント（JS、CSS、画像など）
# staticディレクトリが存在する場合のみマウント
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# APIルーターを追加
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """メインページ。"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "AI Game Sound Generator",
        },
    )


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント。"""
    return {"status": "healthy"}
