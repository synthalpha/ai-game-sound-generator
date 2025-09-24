"""
モニタリング・レポート機能。

稼働状況や生成統計をSlackに通知。
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from src.utils.session_manager import session_manager


class MonitoringService:
    """モニタリングサービス。"""

    def __init__(self, slack_webhook_url: str | None = None):
        """
        初期化。

        Args:
            slack_webhook_url: Slack Webhook URL
        """
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.start_time = datetime.now()
        self.generation_count = 0
        self.error_count = 0
        self.demo_generation_count = 0
        self.rate_limited_count = 0

        # 時間帯別統計
        self.hourly_stats: dict[int, int] = {}

    async def send_slack_notification(self, message: dict[str, Any]) -> bool:
        """
        Slackに通知を送信。

        Args:
            message: 送信するメッセージ

        Returns:
            送信成功の場合True
        """
        if not self.slack_webhook_url:
            print("Slack Webhook URLが設定されていません")
            return False

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    self.slack_webhook_url,
                    json=message,
                    headers={"Content-Type": "application/json"},
                ) as response,
            ):
                return response.status == 200
        except Exception as e:
            print(f"Slack通知エラー: {e}")
            return False

    def increment_generation(self, is_demo: bool = False):
        """生成カウントを増加。"""
        self.generation_count += 1
        if is_demo:
            self.demo_generation_count += 1

        # 時間帯別カウント
        current_hour = datetime.now().hour
        if current_hour not in self.hourly_stats:
            self.hourly_stats[current_hour] = 0
        self.hourly_stats[current_hour] += 1

    def increment_error(self):
        """エラーカウントを増加。"""
        self.error_count += 1

    def increment_rate_limited(self):
        """レート制限カウントを増加。"""
        self.rate_limited_count += 1

    def get_system_stats(self) -> dict[str, Any]:
        """
        システム統計を取得。

        Returns:
            統計情報
        """
        uptime = datetime.now() - self.start_time
        uptime_hours = uptime.total_seconds() / 3600

        # セッション統計
        session_stats = session_manager.get_session_stats()

        # メモリ使用量（簡易）
        import psutil

        memory = psutil.virtual_memory()

        return {
            "uptime_hours": round(uptime_hours, 2),
            "total_generations": self.generation_count,
            "demo_generations": self.demo_generation_count,
            "visitor_generations": self.generation_count - self.demo_generation_count,
            "error_count": self.error_count,
            "rate_limited_count": self.rate_limited_count,
            "active_sessions": session_stats.get("total_sessions", 0),
            "total_files": session_stats.get("total_files", 0),
            "storage_mb": round(session_stats.get("total_size_mb", 0), 2),
            "memory_percent": round(memory.percent, 1),
            "hourly_distribution": self.hourly_stats,
        }

    async def send_hourly_report(self):
        """1時間ごとのレポートを送信。"""
        stats = self.get_system_stats()

        # 前の1時間の統計
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)

        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 AI Game Sound Generator - 定期レポート",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*期間:*\n{hour_ago.strftime('%H:%M')} - {now.strftime('%H:%M')}",
                        },
                        {"type": "mrkdwn", "text": f"*稼働時間:*\n{stats['uptime_hours']}時間"},
                    ],
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*総生成数:*\n{stats['total_generations']}回"},
                        {"type": "mrkdwn", "text": f"*デモ機:*\n{stats['demo_generations']}回"},
                        {"type": "mrkdwn", "text": f"*来場者:*\n{stats['visitor_generations']}回"},
                        {
                            "type": "mrkdwn",
                            "text": f"*レート制限:*\n{stats['rate_limited_count']}回",
                        },
                    ],
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*アクティブセッション:*\n{stats['active_sessions']}",
                        },
                        {"type": "mrkdwn", "text": f"*保存ファイル:*\n{stats['total_files']}個"},
                        {"type": "mrkdwn", "text": f"*ストレージ:*\n{stats['storage_mb']} MB"},
                        {"type": "mrkdwn", "text": f"*メモリ:*\n{stats['memory_percent']}%"},
                    ],
                },
            ]
        }

        # エラーがある場合は警告
        if stats["error_count"] > 0:
            message["blocks"].append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"⚠️ *エラー発生:* {stats['error_count']}件"},
                }
            )

        await self.send_slack_notification(message)

    async def send_daily_summary(self):
        """日次サマリーレポートを送信。"""
        stats = self.get_system_stats()

        # ピーク時間帯を特定
        if self.hourly_stats:
            peak_hour = max(self.hourly_stats, key=self.hourly_stats.get)
            peak_count = self.hourly_stats[peak_hour]
        else:
            peak_hour = 0
            peak_count = 0

        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "📈 日次サマリーレポート"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*日付:* {datetime.now().strftime('%Y年%m月%d日')}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*総生成数:*\n{stats['total_generations']}回"},
                        {
                            "type": "mrkdwn",
                            "text": f"*ピーク時間帯:*\n{peak_hour}時台 ({peak_count}回)",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*生成内訳:*\n• デモ機: {stats['demo_generations']}回 ({stats['demo_generations'] * 100 // max(stats['total_generations'], 1)}%)\n• 来場者: {stats['visitor_generations']}回 ({stats['visitor_generations'] * 100 // max(stats['total_generations'], 1)}%)",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*システム状況:*\n• エラー: {stats['error_count']}件\n• レート制限: {stats['rate_limited_count']}件\n• メモリ使用率: {stats['memory_percent']}%",
                    },
                },
            ]
        }

        await self.send_slack_notification(message)

    async def send_alert(self, alert_type: str, message: str):
        """
        アラート通知を送信。

        Args:
            alert_type: アラートタイプ（error, warning, info）
            message: アラートメッセージ
        """
        emoji = {"error": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(alert_type, "📢")

        slack_message = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{alert_type.upper()}*: {message}",
                    },
                }
            ]
        }

        await self.send_slack_notification(slack_message)


# グローバルインスタンス
monitoring_service = MonitoringService()


async def start_monitoring_tasks():
    """モニタリングタスクを開始。"""

    async def hourly_task():
        """1時間ごとのタスク。"""
        while True:
            await asyncio.sleep(3600)  # 1時間
            try:
                await monitoring_service.send_hourly_report()
            except Exception as e:
                print(f"定期レポートエラー: {e}")

    async def daily_task():
        """日次タスク。"""
        while True:
            # 次の午前9時まで待機
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            next_9am = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            if now.hour >= 9:
                next_9am = next_9am
            else:
                next_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)

            wait_seconds = (next_9am - now).total_seconds()
            await asyncio.sleep(wait_seconds)

            try:
                await monitoring_service.send_daily_summary()
            except Exception as e:
                print(f"日次レポートエラー: {e}")

    # タスクを並行実行
    asyncio.create_task(hourly_task())
    asyncio.create_task(daily_task())
