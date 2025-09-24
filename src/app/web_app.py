"""
FastAPIベースのWebアプリケーション。

モダンなUI/UXを提供するWebインターフェース。
"""

import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Cookie, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.adapters.controllers.audio_generation.api import router as api_router
from src.infrastructure.database import close_db, init_db
from src.utils.monitoring import monitoring_service, start_monitoring_tasks
from src.utils.session_manager import session_manager

# FastAPIアプリケーション初期化
app = FastAPI(
    title="AI Game Sound Generator",
    description="Tokyo Game Show 2025 Demo",
    version="1.0.0",
)

# セッション管理用の辞書（本番環境ではRedisなどを使用）
sessions = {}

# 環境変数からパスワードを取得（デフォルト: tgs2025）
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "tgs2025")
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"

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


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理。"""
    import platform

    # データベースの初期化
    await init_db()
    print("Database initialized")

    # セッションクリーンアップタスクを開始
    await session_manager.start_cleanup_task()
    print("Session cleanup task started")

    # Slack通知が設定されている場合はモニタリングタスクを開始
    if os.getenv("SLACK_WEBHOOK_URL"):
        await start_monitoring_tasks()

        # デプロイ環境の情報を収集
        env_info = {
            "environment": os.getenv("APP_ENV", "production"),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "api_port": os.getenv("API_PORT", "8000"),
            "elevenlabs_configured": bool(os.getenv("ELEVENLABS_API_KEY")),
            "demo_ips": os.getenv("DEMO_IP_ADDRESSES", "未設定"),
        }

        # 起動通知を送信
        startup_message = (
            f"🚀 **AI Game Sound Generator が起動しました**\n"
            f"• 環境: {env_info['environment']}\n"
            f"• ホスト: {env_info['hostname']}\n"
            f"• ポート: {env_info['api_port']}\n"
            f"• ElevenLabs: {'✅ 設定済み' if env_info['elevenlabs_configured'] else '❌ 未設定'}\n"
            f"• デモ機IP: {env_info['demo_ips']}"
        )
        await monitoring_service.send_alert("info", startup_message)


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション停止時の処理。"""
    # Slack通知を送信
    if os.getenv("SLACK_WEBHOOK_URL"):
        await monitoring_service.send_alert("warning", "⚠️ AI Game Sound Generator が停止します")

    # セッションクリーンアップタスクを停止
    await session_manager.stop_cleanup_task()
    print("Session cleanup task stopped")

    # データベース接続をクローズ
    await close_db()
    print("Database connection closed")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """ログインページ。"""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "title": "ログイン - AI Game Sound Generator",
            "error": False,
        },
    )


@app.post("/login")
async def login(
    request: Request,
    password: str = Form(...),
):
    """ログイン処理。"""
    if password == AUTH_PASSWORD:
        # セッショントークンを生成
        session_token = secrets.token_urlsafe(32)
        sessions[session_token] = {
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
        }

        # リダイレクトレスポンスを作成
        redirect = RedirectResponse(url="/", status_code=303)
        redirect.set_cookie(
            key="session",
            value=session_token,
            max_age=86400,  # 24時間
            httponly=True,
            samesite="lax",
        )
        return redirect
    else:
        # パスワードが間違っている場合
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": "ログイン - AI Game Sound Generator",
                "error": True,
            },
        )


@app.get("/logout")
async def logout():
    """ログアウト処理。"""
    redirect = RedirectResponse(url="/login", status_code=303)
    redirect.delete_cookie("session")
    return redirect


def check_auth(session: str | None = None) -> bool:
    """認証チェック。"""
    if not AUTH_ENABLED:
        return True

    if not session:
        return False

    if session not in sessions:
        return False

    # セッションの有効期限をチェック
    session_data = sessions[session]
    if datetime.now() > session_data["expires_at"]:
        del sessions[session]
        return False

    return True


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    session: str | None = Cookie(None),
):
    """メインページ。"""
    # 認証チェック
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "AI Game Sound Generator",
        },
    )


@app.get("/about", response_class=HTMLResponse)
async def about(
    request: Request,
    session: str | None = Cookie(None),
):
    """特徴ページ。"""
    # 認証チェック
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "title": "特徴 - AI Game Sound Generator",
        },
    )


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント。"""
    return {"status": "healthy"}
