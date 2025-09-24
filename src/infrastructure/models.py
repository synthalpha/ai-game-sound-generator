"""
データベースモデル定義。

TGS2025の統計データ管理。
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from src.infrastructure.database import Base


class GenerationLog(Base):
    """音楽生成ログテーブル。"""

    __tablename__ = "generation_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 基本情報
    session_id = Column(String(64), index=True)
    request_id = Column(String(36), unique=True, index=True)  # UUID
    timestamp = Column(DateTime, default=func.now(), index=True)

    # クライアント情報
    ip_address = Column(String(45))  # IPv6対応
    is_demo_machine = Column(Boolean, default=False)
    user_agent = Column(String(256))

    # リクエスト情報
    genre_tags = Column(JSON, default=list)  # ["Electronic", "Ambient"]
    mood_tags = Column(JSON, default=list)  # ["Happy", "Energetic"]
    scene_tags = Column(JSON, default=list)  # ["Battle", "Victory"]
    instrument_tags = Column(JSON, default=list)  # ["Piano", "Synthesizer"]
    tempo_tags = Column(JSON, default=list)  # ["Fast", "120BPM"]
    era_tags = Column(JSON, default=list)  # ["80s", "Modern"]
    region_tags = Column(JSON, default=list)  # ["Japanese", "Celtic"]
    all_tags = Column(JSON, default=list)  # すべてのタグを結合
    tag_count = Column(Integer, default=0)  # 選択されたタグの総数
    duration_seconds = Column(Integer)

    # プロンプト
    generated_prompt = Column(Text)

    # レスポンス情報
    success = Column(Boolean, default=True)
    generation_time = Column(Float)  # 生成にかかった時間（秒）
    file_size_bytes = Column(Integer)
    download_id = Column(String(36))

    # エラー情報
    error_message = Column(Text, nullable=True)
    error_type = Column(String(50), nullable=True)  # rate_limit, api_error, etc

    # メタ情報
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SessionLog(Base):
    """セッションログテーブル。"""

    __tablename__ = "session_logs"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String(64), unique=True, index=True)
    ip_address = Column(String(45))
    is_demo_machine = Column(Boolean, default=False)

    # セッション統計
    first_access = Column(DateTime, default=func.now())
    last_access = Column(DateTime, default=func.now())
    total_generations = Column(Integer, default=0)
    successful_generations = Column(Integer, default=0)
    failed_generations = Column(Integer, default=0)
    total_downloads = Column(Integer, default=0)

    # レート制限
    rate_limited_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class DownloadLog(Base):
    """ダウンロードログテーブル。"""

    __tablename__ = "download_logs"

    id = Column(Integer, primary_key=True, index=True)

    download_id = Column(String(36), index=True)
    session_id = Column(String(64), index=True)
    generation_request_id = Column(String(36))  # 元の生成リクエストID

    timestamp = Column(DateTime, default=func.now())
    ip_address = Column(String(45))
    user_agent = Column(String(256))

    # QRコード経由かどうか
    is_qr_download = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())


class SystemMetrics(Base):
    """システムメトリクステーブル（5分ごとの集計）。"""

    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(DateTime, default=func.now(), index=True)

    # 5分間の統計
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)

    # パフォーマンス
    avg_generation_time = Column(Float)
    max_generation_time = Column(Float)
    min_generation_time = Column(Float)

    # システムリソース
    memory_usage_percent = Column(Float)
    active_sessions = Column(Integer)

    # レート制限
    rate_limited_requests = Column(Integer, default=0)

    created_at = Column(DateTime, default=func.now())
