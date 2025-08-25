"""
ロギング設定モジュール。

アプリケーション全体で使用するロガーの設定を提供します。
"""

import logging
import sys
from pathlib import Path
from typing import Any

from src.di_container.container import get_container


class ColoredFormatter(logging.Formatter):
    """カラー付きフォーマッター。"""

    # ANSIカラーコード
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """ログメッセージをフォーマット。"""
        # 開発環境でのみカラーを適用
        container = get_container()
        if container.config.is_development() and sys.stdout.isatty():
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
                record.msg = f"{self.COLORS[levelname]}{record.msg}{self.RESET}"

        return super().format(record)


class StructuredLogger:
    """構造化ログ出力ラッパー。"""

    def __init__(self, logger: logging.Logger) -> None:
        """初期化。"""
        self._logger = logger

    def debug(self, message: str, **context: Any) -> None:
        """デバッグログを出力。"""
        self._log(logging.DEBUG, message, **context)

    def info(self, message: str, **context: Any) -> None:
        """情報ログを出力。"""
        self._log(logging.INFO, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        """警告ログを出力。"""
        self._log(logging.WARNING, message, **context)

    def error(self, message: str, exception: Exception | None = None, **context: Any) -> None:
        """エラーログを出力。"""
        if exception:
            context["exception"] = str(exception)
            context["exception_type"] = type(exception).__name__
        self._log(logging.ERROR, message, exc_info=exception, **context)

    def critical(self, message: str, **context: Any) -> None:
        """重大エラーログを出力。"""
        self._log(logging.CRITICAL, message, **context)

    def _log(self, level: int, message: str, exc_info: Any = None, **context: Any) -> None:
        """ログを出力。"""
        extra = {"context": context} if context else {}
        self._logger.log(level, message, exc_info=exc_info, extra=extra)


def get_logger(name: str | None = None) -> StructuredLogger:
    """ロガーを取得。

    Args:
        name: ロガー名（Noneの場合は呼び出し元のモジュール名）

    Returns:
        構造化ロガー
    """
    if name is None:
        import inspect

        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get("__name__", "unknown")

    logger = logging.getLogger(name)
    return StructuredLogger(logger)


def setup_logger(
    name: str | None = None,
    level: int | None = None,
    format_string: str | None = None,
    log_file: Path | None = None,
    use_color: bool = True,
) -> logging.Logger:
    """ロガーをセットアップ。

    Args:
        name: ロガー名
        level: ログレベル
        format_string: フォーマット文字列
        log_file: ログファイルパス
        use_color: カラー出力を使用するか

    Returns:
        設定済みロガー
    """
    container = get_container()
    config = container.config.logging

    # デフォルト値を設定
    if level is None:
        level = getattr(logging, config.level.upper(), logging.INFO)
    if format_string is None:
        format_string = config.format
    if log_file is None:
        log_file = config.file_path

    # ロガーを取得
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    # フォーマッターを選択
    formatter: logging.Formatter
    if use_color and container.config.is_development():
        formatter = ColoredFormatter(format_string)
    else:
        formatter = logging.Formatter(format_string)

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラー（設定されている場合）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(format_string))  # ファイルは常に色なし
        logger.addHandler(file_handler)

    return logger


def log_function_call(func_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    """関数呼び出しをログ出力。

    Args:
        func_name: 関数名
        args: 位置引数
        kwargs: キーワード引数
    """
    logger = get_logger()
    logger.debug(
        f"Function called: {func_name}",
        args=args,
        kwargs=kwargs,
    )


def log_function_result(func_name: str, result: Any, duration: float) -> None:
    """関数結果をログ出力。

    Args:
        func_name: 関数名
        result: 戻り値
        duration: 実行時間（秒）
    """
    logger = get_logger()
    logger.debug(
        f"Function completed: {func_name}",
        result=str(result)[:100],  # 長い結果は切り詰め
        duration_ms=duration * 1000,
    )


def log_function_error(func_name: str, error: Exception) -> None:
    """関数エラーをログ出力。

    Args:
        func_name: 関数名
        error: 発生した例外
    """
    logger = get_logger()
    logger.error(
        f"Function failed: {func_name}",
        exception=error,
    )
