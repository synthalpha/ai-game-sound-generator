"""
音楽ファイルストレージリポジトリ。

生成された音楽ファイルの保存と管理を行います。
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from src.entities.music_generation import MusicFile, MusicGenerationRequest


class MusicFileStorageRepository:
    """音楽ファイルストレージリポジトリ。

    ローカルファイルシステムに音楽ファイルを保存し、
    メタデータをJSON形式で管理します。
    """

    def __init__(self, base_path: str | Path) -> None:
        """初期化。

        Args:
            base_path: ストレージのベースパス
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # メタデータファイルのパス
        self.metadata_file = self.base_path / "metadata.json"
        self.metadata = self._load_metadata()

        self._logger = logging.getLogger(__name__)

    def save(
        self,
        music_file: MusicFile,
        request: MusicGenerationRequest,
        tags: list[str] | None = None,
    ) -> str:
        """音楽ファイルを保存。

        Args:
            music_file: 保存する音楽ファイル
            request: 生成リクエスト
            tags: タグリスト（オプション）

        Returns:
            保存されたファイルのID

        Raises:
            ValueError: ファイルデータがない場合
        """
        if not music_file.data:
            raise ValueError("音楽ファイルのデータがありません")

        # ファイルIDを生成（ハッシュベース）
        file_id = self._generate_file_id(music_file.data)

        # ファイルパスを決定
        file_dir = self.base_path / file_id[:2] / file_id[2:4]
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir / f"{file_id}.mp3"

        # ファイルを保存
        file_path.write_bytes(music_file.data)

        # メタデータを保存
        metadata_entry = {
            "id": file_id,
            "file_name": music_file.file_name,
            "file_path": str(file_path.relative_to(self.base_path)),
            "file_size_bytes": music_file.file_size_bytes,
            "duration_seconds": music_file.duration_seconds,
            "format": music_file.format,
            "prompt": request.prompt,
            "style": request.style.value if request.style else None,
            "mood": request.mood.value if request.mood else None,
            "tempo": request.tempo.value if request.tempo else None,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
        }

        self.metadata[file_id] = metadata_entry
        self._save_metadata()

        self._logger.info(
            f"音楽ファイルを保存しました: {file_id}",
            extra={"file_size": music_file.file_size_bytes},
        )

        return file_id

    def load(self, file_id: str) -> MusicFile | None:
        """音楽ファイルを読み込み。

        Args:
            file_id: ファイルID

        Returns:
            音楽ファイル（存在しない場合はNone）
        """
        if file_id not in self.metadata:
            return None

        entry = self.metadata[file_id]
        file_path = self.base_path / entry["file_path"]

        if not file_path.exists():
            self._logger.warning(f"ファイルが見つかりません: {file_path}")
            return None

        # ファイルデータを読み込み
        data = file_path.read_bytes()

        return MusicFile(
            file_name=entry["file_name"],
            file_size_bytes=entry["file_size_bytes"],
            duration_seconds=entry["duration_seconds"],
            format=entry["format"],
            data=data,
        )

    def delete(self, file_id: str) -> bool:
        """音楽ファイルを削除。

        Args:
            file_id: ファイルID

        Returns:
            削除成功の場合True
        """
        if file_id not in self.metadata:
            return False

        entry = self.metadata[file_id]
        file_path = self.base_path / entry["file_path"]

        # ファイルを削除
        if file_path.exists():
            file_path.unlink()

        # メタデータから削除
        del self.metadata[file_id]
        self._save_metadata()

        self._logger.info(f"音楽ファイルを削除しました: {file_id}")

        return True

    def list_files(
        self,
        style: str | None = None,
        mood: str | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """音楽ファイルのリストを取得。

        Args:
            style: スタイルでフィルタ
            mood: ムードでフィルタ
            tags: タグでフィルタ
            limit: 取得件数の上限

        Returns:
            メタデータのリスト
        """
        results = []

        for _file_id, entry in self.metadata.items():
            # フィルタ条件をチェック
            if style and entry.get("style") != style:
                continue
            if mood and entry.get("mood") != mood:
                continue
            if tags:
                entry_tags = set(entry.get("tags", []))
                if not entry_tags.intersection(set(tags)):
                    continue

            results.append(entry)

            if len(results) >= limit:
                break

        # 作成日時でソート（新しい順）
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return results

    def get_metadata(self, file_id: str) -> dict | None:
        """メタデータを取得。

        Args:
            file_id: ファイルID

        Returns:
            メタデータ（存在しない場合はNone）
        """
        return self.metadata.get(file_id)

    def update_tags(self, file_id: str, tags: list[str]) -> bool:
        """タグを更新。

        Args:
            file_id: ファイルID
            tags: 新しいタグリスト

        Returns:
            更新成功の場合True
        """
        if file_id not in self.metadata:
            return False

        self.metadata[file_id]["tags"] = tags
        self.metadata[file_id]["updated_at"] = datetime.now().isoformat()
        self._save_metadata()

        return True

    def get_storage_stats(self) -> dict:
        """ストレージ統計を取得。

        Returns:
            統計情報
        """
        total_files = len(self.metadata)
        total_size = sum(entry.get("file_size_bytes", 0) for entry in self.metadata.values())
        total_duration = sum(entry.get("duration_seconds", 0) for entry in self.metadata.values())

        # スタイル別の統計
        style_stats = {}
        for entry in self.metadata.values():
            style = entry.get("style", "unknown")
            if style not in style_stats:
                style_stats[style] = 0
            style_stats[style] += 1

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "total_duration_seconds": total_duration,
            "total_duration_minutes": total_duration / 60,
            "style_distribution": style_stats,
        }

    def cleanup_orphaned_files(self) -> int:
        """メタデータに存在しないファイルを削除。

        Returns:
            削除されたファイル数
        """
        deleted_count = 0

        # メタデータに記録されているファイルパスのセット
        metadata_paths = {self.base_path / entry["file_path"] for entry in self.metadata.values()}

        # 実際のファイルを走査
        for file_path in self.base_path.rglob("*.mp3"):
            if file_path not in metadata_paths:
                self._logger.info(f"孤立ファイルを削除: {file_path}")
                file_path.unlink()
                deleted_count += 1

        return deleted_count

    def _generate_file_id(self, data: bytes) -> str:
        """ファイルIDを生成。

        Args:
            data: ファイルデータ

        Returns:
            ファイルID（SHA256ハッシュの16進数）
        """
        return hashlib.sha256(data).hexdigest()

    def _load_metadata(self) -> dict:
        """メタデータを読み込み。

        Returns:
            メタデータ辞書
        """
        if not self.metadata_file.exists():
            return {}

        try:
            with open(self.metadata_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self._logger.error(f"メタデータの読み込みに失敗: {e}")
            return {}

    def _save_metadata(self) -> None:
        """メタデータを保存。"""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._logger.error(f"メタデータの保存に失敗: {e}")
