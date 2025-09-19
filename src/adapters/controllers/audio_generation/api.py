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
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.adapters.gateways.elevenlabs import ElevenLabs
from src.adapters.repositories.prompt_repository import PromptRepository
from src.adapters.repositories.tag_repository import TagRepository
from src.di_container.config import ElevenLabsConfig
from src.entities.music_generation import MusicGenerationRequest
from src.entities.prompt import PromptType
from src.usecases.prompt_generation.generate_prompt import GeneratePromptUseCase

# 環境変数を読み込み
load_dotenv()

router = APIRouter(prefix="/api")

# ファイル保存ディレクトリ
DOWNLOAD_DIR = Path("/tmp/music_downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# 現在のダウンロードファイル（1つのみ保持）
current_download_file = {"id": None, "path": None, "filename": None}


def cleanup_old_files():
    """古いファイルを削除。"""
    global current_download_file
    if current_download_file["path"] and Path(current_download_file["path"]).exists():
        try:
            Path(current_download_file["path"]).unlink()
        except Exception as e:
            print(f"ファイル削除エラー: {e}")
    current_download_file = {"id": None, "path": None, "filename": None}


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


@router.post("/generate", response_model=GenerateMusicResponse)
async def generate_music(request: GenerateMusicRequest) -> GenerateMusicResponse:
    """音楽を生成。"""
    import time

    start_time = time.time()

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

        # 実際の音楽生成
        config = ElevenLabsConfig(api_key=api_key)
        elevenlabs = ElevenLabs(config)

        music_request = MusicGenerationRequest(
            prompt=prompt.text,
            duration_seconds=request.duration_seconds,
        )

        music_file = await elevenlabs.compose_music(music_request, output_format="mp3")

        print(
            f"Generated music file: {music_file.file_name}, size: {music_file.file_size_bytes}, duration: {music_file.duration_seconds}"
        )  # デバッグ

        # 音声データをBase64エンコード
        audio_data_base64 = (
            base64.b64encode(music_file.data).decode("utf-8") if music_file.data else None
        )

        # 古いファイルを削除
        cleanup_old_files()

        # 新しいファイルを保存
        download_id = str(uuid.uuid4())
        if music_file.data:
            file_path = DOWNLOAD_DIR / f"{download_id}.mp3"
            file_path.write_bytes(music_file.data)

            # 現在のダウンロード情報を更新
            global current_download_file
            current_download_file = {
                "id": download_id,
                "path": str(file_path),
                "filename": music_file.file_name,
            }

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
async def download_music(download_id: str):
    """生成した音楽ファイルをダウンロード。"""
    global current_download_file

    # ダウンロードIDが一致するか確認
    if not current_download_file["id"] or current_download_file["id"] != download_id:
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")

    # ファイルが存在するか確認
    file_path = Path(current_download_file["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")

    return FileResponse(
        path=file_path,
        filename=current_download_file["filename"],
        media_type="audio/mpeg",
    )


@router.delete("/cleanup")
async def cleanup_files():
    """ファイルをクリーンアップ。"""
    cleanup_old_files()
    return {"status": "cleaned"}


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
