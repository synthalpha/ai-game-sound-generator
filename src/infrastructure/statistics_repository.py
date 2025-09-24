"""
統計データリポジトリ。

データベースへの統計情報の保存と取得。
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Integer, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.models import DownloadLog, GenerationLog, SessionLog, SystemMetrics


class StatisticsRepository:
    """統計データリポジトリ。"""

    def __init__(self, session: AsyncSession):
        """
        初期化。

        Args:
            session: データベースセッション
        """
        self.session = session

    async def log_generation(
        self,
        session_id: str,
        ip_address: str,
        is_demo: bool,
        request_data: dict[str, Any],
        response_data: dict[str, Any],
        prompt: str,
        generation_time: float,
    ) -> str:
        """
        生成ログを記録。

        Args:
            session_id: セッションID
            ip_address: IPアドレス
            is_demo: デモ機かどうか
            request_data: リクエストデータ
            response_data: レスポンスデータ
            prompt: 生成されたプロンプト
            generation_time: 生成時間

        Returns:
            リクエストID
        """
        request_id = str(uuid.uuid4())

        try:
            # すべてのタグを結合
            all_tags = []
            for key in [
                "genre_tags",
                "mood_tags",
                "scene_tags",
                "instrument_tags",
                "tempo_tags",
                "era_tags",
                "region_tags",
            ]:
                if key in request_data and request_data[key]:
                    all_tags.extend(request_data[key])

            log = GenerationLog(
                session_id=session_id,
                request_id=request_id,
                ip_address=ip_address,
                is_demo_machine=is_demo,
                genre_tags=request_data.get("genre_tags", []),
                mood_tags=request_data.get("mood_tags", []),
                scene_tags=request_data.get("scene_tags", []),
                instrument_tags=request_data.get("instrument_tags", []),
                tempo_tags=request_data.get("tempo_tags", []),
                era_tags=request_data.get("era_tags", []),
                region_tags=request_data.get("region_tags", []),
                all_tags=all_tags,
                tag_count=len(all_tags),
                duration_seconds=request_data.get("duration_seconds", 10),
                generated_prompt=prompt,
                success=response_data.get("success", False),
                generation_time=generation_time,
                file_size_bytes=response_data.get("file_size_bytes"),
                download_id=response_data.get("download_id"),
                error_message=response_data.get("error_message"),
                error_type=response_data.get("error_type"),
            )

            self.session.add(log)

            # セッションログの更新
            await self.update_session_stats(
                session_id=session_id,
                ip_address=ip_address,
                is_demo=is_demo,
                is_success=response_data.get("success", False),
            )

            await self.session.commit()
            return request_id

        except Exception as e:
            await self.session.rollback()
            print(f"Database error in log_generation: {e}")
            # エラーが起きても処理は継続（ログ記録失敗だけ）
            return str(uuid.uuid4())

    async def log_download(
        self,
        download_id: str,
        session_id: str | None,
        ip_address: str,
        user_agent: str | None,
        is_qr: bool = False,
    ):
        """
        ダウンロードログを記録。

        Args:
            download_id: ダウンロードID
            session_id: セッションID
            ip_address: IPアドレス
            user_agent: ユーザーエージェント
            is_qr: QRコード経由かどうか
        """
        try:
            # 元の生成リクエストを検索
            stmt = select(GenerationLog.request_id).where(GenerationLog.download_id == download_id)
            result = await self.session.execute(stmt)
            request_id = result.scalar()

            log = DownloadLog(
                download_id=download_id,
                session_id=session_id,
                generation_request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent[:256] if user_agent else None,  # 長さ制限
                is_qr_download=is_qr,
            )

            self.session.add(log)

            # セッションログのダウンロード数を更新
            if session_id:
                stmt = select(SessionLog).where(SessionLog.session_id == session_id)
                result = await self.session.execute(stmt)
                session = result.scalar_one_or_none()
                if session:
                    session.total_downloads += 1

            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            print(f"Database error in log_download: {e}")
            # エラーが起きても処理は継続

    async def update_session_stats(
        self,
        session_id: str,
        ip_address: str,
        is_demo: bool,
        is_success: bool,
    ):
        """
        セッション統計を更新。

        Args:
            session_id: セッションID
            ip_address: IPアドレス
            is_demo: デモ機かどうか
            is_success: 成功したかどうか
        """
        stmt = select(SessionLog).where(SessionLog.session_id == session_id)
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            # 新規セッション
            session = SessionLog(
                session_id=session_id,
                ip_address=ip_address,
                is_demo_machine=is_demo,
                total_generations=1,
                successful_generations=1 if is_success else 0,
                failed_generations=0 if is_success else 1,
            )
            self.session.add(session)
        else:
            # 既存セッション更新
            session.last_access = datetime.now()
            session.total_generations += 1
            if is_success:
                session.successful_generations += 1
            else:
                session.failed_generations += 1

    async def log_rate_limit(self, session_id: str):
        """
        レート制限ログを記録。

        Args:
            session_id: セッションID
        """
        stmt = select(SessionLog).where(SessionLog.session_id == session_id)
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            session.rate_limited_count += 1
            await self.session.commit()

    async def get_popular_tags(self, hours: int = 24, limit: int = 10) -> dict[str, list[tuple]]:
        """
        人気タグを取得。

        Args:
            hours: 過去何時間分
            limit: 取得件数

        Returns:
            カテゴリ別の人気タグリスト
        """
        since = datetime.now() - timedelta(hours=hours)

        result = {}
        tag_categories = ["genre_tags", "mood_tags", "scene_tags", "instrument_tags"]

        # 簡易版：all_tagsから集計
        stmt = select(GenerationLog.all_tags).where(
            and_(GenerationLog.timestamp >= since, GenerationLog.success.is_(True))
        )

        logs = await self.session.execute(stmt)

        # Python側で集計
        tag_counts = {}
        for log in logs:
            if log.all_tags:
                for tag in log.all_tags:
                    if tag not in tag_counts:
                        tag_counts[tag] = 0
                    tag_counts[tag] += 1

        # 上位タグを取得
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

        for category in tag_categories:
            result[category] = sorted_tags

        return result

    async def get_hourly_stats(self, date: datetime) -> list[dict]:
        """
        時間帯別統計を取得。

        Args:
            date: 対象日付

        Returns:
            時間帯別の統計データ
        """
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        stmt = (
            select(
                func.extract("hour", GenerationLog.timestamp).label("hour"),
                func.count().label("total"),
                func.sum(cast(GenerationLog.success, Integer)).label("success"),
                func.avg(GenerationLog.generation_time).label("avg_time"),
            )
            .where(and_(GenerationLog.timestamp >= start_date, GenerationLog.timestamp < end_date))
            .group_by("hour")
            .order_by("hour")
        )

        result = await self.session.execute(stmt)
        return [
            {
                "hour": row.hour,
                "total": row.total,
                "success": row.success or 0,
                "avg_generation_time": round(row.avg_time, 2) if row.avg_time else 0,
            }
            for row in result
        ]

    async def save_system_metrics(
        self,
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
        avg_generation_time: float,
        memory_percent: float,
        active_sessions: int,
        rate_limited: int,
    ):
        """
        システムメトリクスを保存。

        Args:
            各種メトリクス値
        """
        metrics = SystemMetrics(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_generation_time=avg_generation_time,
            memory_usage_percent=memory_percent,
            active_sessions=active_sessions,
            rate_limited_requests=rate_limited,
        )

        self.session.add(metrics)
        await self.session.commit()
