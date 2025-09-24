"""
セッション管理ユーティリティ。

マルチユーザー環境でのセッション管理とファイル分離を提供。
"""

import asyncio
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel


class SessionFile(BaseModel):
    """セッションに紐づくファイル情報。"""

    id: str
    path: str
    filename: str
    created_at: datetime
    size_bytes: int


class SessionData(BaseModel):
    """セッションデータ。"""

    session_id: str
    created_at: datetime
    last_access: datetime
    files: list[SessionFile] = []
    max_files: int = 10  # セッションあたりの最大ファイル数


class SessionManager:
    """
    セッション管理クラス。

    各ユーザーセッションごとにファイルを分離して管理。
    """

    def __init__(
        self,
        base_dir: Path = Path("/tmp/music_sessions"),
        session_ttl_minutes: int = 10,
        max_file_size_mb: int = 50,
        cleanup_interval_minutes: int = 10,
    ):
        """
        初期化。

        Args:
            base_dir: セッションファイルの基底ディレクトリ
            session_ttl_minutes: セッションの有効期限（分）
            max_file_size_mb: ファイルの最大サイズ（MB）
            cleanup_interval_minutes: クリーンアップ実行間隔（分）
        """
        self._base_dir = base_dir
        self._session_ttl = timedelta(minutes=session_ttl_minutes)
        self._max_file_size = max_file_size_mb * 1024 * 1024  # バイトに変換
        self._cleanup_interval = cleanup_interval_minutes * 60  # 秒に変換
        self._sessions: dict[str, SessionData] = {}

        # 基底ディレクトリを作成
        self._base_dir.mkdir(parents=True, exist_ok=True)

        # バックグラウンドクリーンアップタスク
        self._cleanup_task: asyncio.Task | None = None

    async def start_cleanup_task(self):
        """バックグラウンドクリーンアップタスクを開始。"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def stop_cleanup_task(self):
        """バックグラウンドクリーンアップタスクを停止。"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            import contextlib

            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def _periodic_cleanup(self):
        """定期的なクリーンアップ処理。"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"クリーンアップエラー: {e}")

    def get_or_create_session(self, session_id: str) -> SessionData:
        """
        セッションを取得または作成。

        Args:
            session_id: セッションID

        Returns:
            セッションデータ
        """
        if session_id not in self._sessions:
            # 新規セッション作成
            session_dir = self._base_dir / session_id
            session_dir.mkdir(exist_ok=True)

            self._sessions[session_id] = SessionData(
                session_id=session_id,
                created_at=datetime.now(),
                last_access=datetime.now(),
            )
        else:
            # 既存セッションの最終アクセス時刻を更新
            self._sessions[session_id].last_access = datetime.now()

        return self._sessions[session_id]

    def add_file_to_session(
        self,
        session_id: str,
        file_id: str,
        file_path: str,
        filename: str,
        size_bytes: int,
    ) -> SessionFile:
        """
        セッションにファイルを追加。

        Args:
            session_id: セッションID
            file_id: ファイルID
            file_path: ファイルパス
            filename: ファイル名
            size_bytes: ファイルサイズ（バイト）

        Returns:
            追加されたファイル情報

        Raises:
            ValueError: ファイルサイズが制限を超える場合
        """
        if size_bytes > self._max_file_size:
            raise ValueError(
                f"ファイルサイズが制限（{self._max_file_size // 1024 // 1024}MB）を超えています"
            )

        session = self.get_or_create_session(session_id)

        # ファイル数制限チェック
        if len(session.files) >= session.max_files:
            # 最も古いファイルを削除
            oldest_file = min(session.files, key=lambda f: f.created_at)
            self.remove_file_from_session(session_id, oldest_file.id)

        # 新しいファイルを追加
        session_file = SessionFile(
            id=file_id,
            path=file_path,
            filename=filename,
            created_at=datetime.now(),
            size_bytes=size_bytes,
        )
        session.files.append(session_file)

        return session_file

    def get_session_file(self, session_id: str, file_id: str) -> SessionFile | None:
        """
        セッションからファイルを取得。

        Args:
            session_id: セッションID
            file_id: ファイルID

        Returns:
            ファイル情報（存在しない場合はNone）
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]
        for file in session.files:
            if file.id == file_id:
                session.last_access = datetime.now()
                return file

        return None

    def remove_file_from_session(self, session_id: str, file_id: str) -> bool:
        """
        セッションからファイルを削除。

        Args:
            session_id: セッションID
            file_id: ファイルID

        Returns:
            削除成功の場合True
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        for i, file in enumerate(session.files):
            if file.id == file_id:
                # ファイルを物理削除
                try:
                    Path(file.path).unlink(missing_ok=True)
                except Exception as e:
                    print(f"ファイル削除エラー: {e}")

                # セッションから削除
                session.files.pop(i)
                return True

        return False

    async def cleanup_expired_sessions(self) -> int:
        """
        期限切れセッションをクリーンアップ。

        Returns:
            削除されたセッション数
        """
        now = datetime.now()
        expired_sessions = []

        for session_id, session in self._sessions.items():
            if now - session.last_access > self._session_ttl:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.delete_session(session_id)

        return len(expired_sessions)

    async def delete_session(self, session_id: str) -> bool:
        """
        セッションを完全削除。

        Args:
            session_id: セッションID

        Returns:
            削除成功の場合True
        """
        if session_id not in self._sessions:
            return False

        # セッションディレクトリを削除
        session_dir = self._base_dir / session_id
        try:
            if session_dir.exists():
                shutil.rmtree(session_dir)
        except Exception as e:
            print(f"セッションディレクトリ削除エラー: {e}")

        # メモリから削除
        del self._sessions[session_id]
        return True

    def get_session_stats(self) -> dict:
        """
        セッション統計情報を取得。

        Returns:
            統計情報
        """
        total_files = 0
        total_size = 0

        for session in self._sessions.values():
            total_files += len(session.files)
            total_size += sum(f.size_bytes for f in session.files)

        return {
            "total_sessions": len(self._sessions),
            "total_files": total_files,
            "total_size_mb": total_size / 1024 / 1024,
            "base_dir": str(self._base_dir),
        }


# グローバルインスタンス（アプリケーション起動時に初期化）
session_manager = SessionManager()
