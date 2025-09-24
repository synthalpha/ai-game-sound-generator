"""
FastAPI APIルート定義。

音楽生成のためのAPIエンドポイント。
"""

import base64
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.adapters.gateways.elevenlabs import ElevenLabs
from src.adapters.repositories.prompt_repository import PromptRepository
from src.adapters.repositories.tag_repository import TagRepository
from src.di_container.config import ElevenLabsConfig
from src.entities.music_generation import MusicGenerationRequest
from src.entities.prompt import PromptType
from src.usecases.prompt_generation.generate_prompt import GeneratePromptUseCase
from src.utils.session_manager import session_manager

# 環境変数を読み込み
load_dotenv()

router = APIRouter(prefix="/api")


def get_session_id(request: Request, session: str | None = Cookie(None)) -> str:
    """
    セッションIDを取得（存在しない場合は作成）。

    Args:
        request: FastAPIリクエスト
        session: セッションCookie

    Returns:
        セッションID
    """
    # Cookieからセッションを取得、なければ新規作成
    if not session:
        # IPアドレスとタイムスタンプを元に生成
        import hashlib
        import time

        client_ip = request.client.host if request.client else "unknown"
        session = hashlib.md5(f"{client_ip}_{time.time()}".encode()).hexdigest()
    return session


class GenerateMusicRequest(BaseModel):
    """音楽生成リクエスト。"""

    genre_tags: list[str] = []
    mood_tags: list[str] = []
    scene_tags: list[str] = []
    instrument_tags: list[str] = []
    tempo_tags: list[str] = []
    era_tags: list[str] = []
    region_tags: list[str] = []
    duration_seconds: int = 10


class GenerateMusicResponse(BaseModel):
    """音楽生成レスポンス。"""

    success: bool
    prompt: str
    audio_data: str | None = None  # Base64エンコードされた音声データ
    download_id: str | None = None  # ダウンロード用ID
    file_name: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: int | None = None
    generation_time: float | None = None
    error_message: str | None = None
    expires_in_minutes: int = 10


@router.post("/generate", response_model=GenerateMusicResponse)
async def generate_music(
    request: GenerateMusicRequest,
    http_request: Request,
    session: str | None = Cookie(None),
) -> GenerateMusicResponse:
    """音楽を生成。"""
    import time

    start_time = time.time()
    session_id = get_session_id(http_request, session)

    # デモ機のIPアドレスリストを環境変数から取得
    demo_ip_list = os.getenv("DEMO_IP_ADDRESSES", "").strip()
    demo_ips = [ip.strip() for ip in demo_ip_list.split(",") if ip.strip()]

    # クライアントIPアドレスを取得
    client_ip = http_request.client.host if http_request.client else "unknown"

    # デモ機判定とレート制限チェック
    is_demo_machine = client_ip in demo_ips
    if not is_demo_machine and os.getenv("ELEVENLABS_API_KEY"):
        is_allowed, error_message = session_manager.check_rate_limit(session_id)
        if not is_allowed:
            return GenerateMusicResponse(
                success=False,
                prompt="",
                error_message=error_message,
                generation_time=0,
            )

    # デバッグ用ログ（本番環境では削除推奨）
    if is_demo_machine:
        print(f"Demo machine access from IP: {client_ip}")

    try:
        # リポジトリとユースケース初期化
        tag_repo = TagRepository()
        prompt_repo = PromptRepository()
        prompt_generator = GeneratePromptUseCase(tag_repo, prompt_repo)

        # タグIDリストの作成
        tag_ids = []
        if request.genre_tags:
            tag_ids.extend([f"genre_{tag.lower()}" for tag in request.genre_tags])
        if request.mood_tags:
            tag_ids.extend([f"mood_{tag.lower()}" for tag in request.mood_tags])
        if request.scene_tags:
            tag_ids.extend([f"scene_{tag.lower()}" for tag in request.scene_tags])
        if request.instrument_tags:
            tag_ids.extend([f"instrument_{tag.lower()}" for tag in request.instrument_tags])
        if request.tempo_tags:
            tag_ids.extend([f"tempo_{tag.lower()}" for tag in request.tempo_tags])
        if request.era_tags:
            tag_ids.extend([f"era_{tag.lower()}" for tag in request.era_tags])
        if request.region_tags:
            tag_ids.extend([f"region_{tag.lower()}" for tag in request.region_tags])

        if not tag_ids:
            raise HTTPException(status_code=400, detail="タグを選択してください")

        # プロンプト生成
        prompt = prompt_generator.execute(
            tag_ids,
            prompt_type=PromptType.MUSIC,
            duration_seconds=request.duration_seconds,
        )

        # ElevenLabs API呼び出し
        api_key = os.getenv("ELEVENLABS_API_KEY")
        print(f"API Key found: {bool(api_key)}")  # デバッグ用
        if not api_key:
            # デモモード（APIキーがない場合）
            generation_time = time.time() - start_time
            return GenerateMusicResponse(
                success=True,
                prompt=prompt.text,
                audio_data=None,
                file_name="demo_music.mp3",
                file_size_bytes=2400000,  # 2.4MB
                duration_seconds=request.duration_seconds,
                generation_time=generation_time,
            )

        # 生成統計を更新
        session_manager.update_generation_stats(session_id)

        # 実際の音楽生成
        config = ElevenLabsConfig(api_key=api_key)
        elevenlabs = ElevenLabs(config)

        music_request = MusicGenerationRequest(
            prompt=prompt.text,
            duration_seconds=request.duration_seconds,
        )

        import asyncio

        if asyncio.iscoroutinefunction(elevenlabs.compose_music):
            music_file = await elevenlabs.compose_music(music_request, output_format="mp3")
        else:
            music_file = elevenlabs.compose_music(music_request, output_format="mp3")

        print(
            f"Generated music file: {music_file.file_name}, size: {music_file.file_size_bytes}, duration: {music_file.duration_seconds}"
        )  # デバッグ

        # 音声データをBase64エンコード
        audio_data_base64 = (
            base64.b64encode(music_file.data).decode("utf-8") if music_file.data else None
        )

        # ファイルをセッション別に保存（ダウンロード用）
        download_id = str(uuid.uuid4())
        if music_file.data:
            # セッション別ディレクトリに保存
            session_manager.get_or_create_session(session_id)
            session_dir = Path(f"/tmp/music_sessions/{session_id}")
            session_dir.mkdir(parents=True, exist_ok=True)

            file_path = session_dir / f"{download_id}.mp3"
            file_path.write_bytes(music_file.data)

            # セッションにファイル情報を追加
            session_manager.add_file_to_session(
                session_id=session_id,
                file_id=download_id,
                file_path=str(file_path),
                filename=music_file.file_name,
                size_bytes=music_file.file_size_bytes,
            )

        generation_time = time.time() - start_time

        return GenerateMusicResponse(
            success=True,
            prompt=prompt.text,
            audio_data=audio_data_base64,
            download_id=download_id,
            file_name=music_file.file_name,
            file_size_bytes=music_file.file_size_bytes,
            duration_seconds=music_file.duration_seconds,
            generation_time=generation_time,
        )

    except Exception as e:
        generation_time = time.time() - start_time
        return GenerateMusicResponse(
            success=False,
            prompt="",
            error_message=str(e),
            generation_time=generation_time,
        )


@router.get("/download/{download_id}")
async def download_music(
    download_id: str,
):
    """生成した音楽ファイルをダウンロード。"""
    # 高速インデックスを使用してファイルを検索
    session_file, session_id = session_manager.get_file_by_id(download_id)

    if session_file:
        file_path = Path(session_file.path)
        if file_path.exists():
            return FileResponse(
                path=file_path,
                filename=session_file.filename,
                media_type="audio/mpeg",
            )
        else:
            # ファイルが物理的に存在しない場合
            if session_id:
                session_manager.remove_file_from_session(session_id, download_id)

    # ファイルが見つからない場合
    raise HTTPException(status_code=404, detail="ファイルが見つかりません")


@router.delete("/cleanup")
async def cleanup_files():
    """期限切れセッションをクリーンアップ。"""
    deleted_count = await session_manager.cleanup_expired_sessions()
    return {"status": "cleaned", "deleted_sessions": deleted_count}


@router.get("/session/stats")
async def get_session_stats():
    """セッション統計情報を取得。"""
    return session_manager.get_session_stats()


@router.get("/tags")
async def get_tags() -> dict[str, Any]:
    """利用可能なタグを取得。"""
    tag_repo = TagRepository()
    categories = tag_repo.get_all_categories()

    result = {}
    for category in categories:
        tags = tag_repo.get_tags_by_category(category.id)
        result[category.id] = {
            "display_name": category.display_name,
            "is_exclusive": category.isExclusive,
            "max_selections": category.maxSelections,
            "tags": [
                {
                    "id": f"{category.id}_{tag.value.name.lower()}",
                    "name": tag.value.name,
                    "name_ja": tag.value.name_ja,
                }
                for tag in tags
            ],
        }

    return result
