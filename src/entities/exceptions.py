"""
ドメイン例外モジュール。

このモジュールでは、ドメイン層で発生する例外を定義します。
"""

from typing import Any


class DomainException(Exception):
    """ドメイン例外の基底クラス。"""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """初期化。"""
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundException(DomainException):
    """エンティティが見つからない場合の例外。"""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        """初期化。"""
        message = f"{entity_type}が見つかりません: {entity_id}"
        super().__init__(message, {"entity_type": entity_type, "entity_id": entity_id})


class DuplicateEntityException(DomainException):
    """エンティティが重複している場合の例外。"""

    def __init__(self, entity_type: str, identifier: str) -> None:
        """初期化。"""
        message = f"{entity_type}が既に存在します: {identifier}"
        super().__init__(message, {"entity_type": entity_type, "identifier": identifier})


class InvalidStateTransitionException(DomainException):
    """無効な状態遷移の例外。"""

    def __init__(self, entity_type: str, current_state: str, target_state: str) -> None:
        """初期化。"""
        message = f"無効な状態遷移: {entity_type} ({current_state} -> {target_state})"
        super().__init__(
            message,
            {
                "entity_type": entity_type,
                "current_state": current_state,
                "target_state": target_state,
            },
        )


class BusinessRuleViolationException(DomainException):
    """ビジネスルール違反の例外。"""

    def __init__(self, rule: str, violation: str) -> None:
        """初期化。"""
        message = f"ビジネスルール違反: {rule} - {violation}"
        super().__init__(message, {"rule": rule, "violation": violation})


class AudioGenerationException(DomainException):
    """音楽生成に関する例外。"""

    def __init__(self, reason: str, audio_id: str | None = None) -> None:
        """初期化。"""
        message = f"音楽生成エラー: {reason}"
        super().__init__(message, {"reason": reason, "audio_id": audio_id})


class TagValidationException(DomainException):
    """タグ検証に関する例外。"""

    def __init__(self, reason: str, tag_value: str | None = None) -> None:
        """初期化。"""
        message = f"タグ検証エラー: {reason}"
        super().__init__(message, {"reason": reason, "tag_value": tag_value})


class PromptGenerationException(DomainException):
    """プロンプト生成に関する例外。"""

    def __init__(self, reason: str, tags: list[str] | None = None) -> None:
        """初期化。"""
        message = f"プロンプト生成エラー: {reason}"
        super().__init__(message, {"reason": reason, "tags": tags})


class QuotaExceededException(DomainException):
    """利用制限超過の例外。"""

    def __init__(
        self, resource: str, limit: int, current: int, reset_at: str | None = None
    ) -> None:
        """初期化。"""
        message = f"利用制限超過: {resource} (現在: {current}/{limit})"
        super().__init__(
            message,
            {
                "resource": resource,
                "limit": limit,
                "current": current,
                "reset_at": reset_at,
            },
        )


class AudioGenerationError(DomainException):
    """音楽生成エラー。"""

    def __init__(self, message: str) -> None:
        """初期化。"""
        super().__init__(message)


class RateLimitError(DomainException):
    """レート制限エラー。"""

    def __init__(self, message: str) -> None:
        """初期化。"""
        super().__init__(message)


class ExternalAPIError(DomainException):
    """外部APIエラー。"""

    def __init__(self, message: str) -> None:
        """初期化。"""
        super().__init__(message)


class ExternalServiceException(DomainException):
    """外部サービスに関する例外。"""

    def __init__(
        self,
        service: str,
        error_type: str,
        error_message: str,
        retry_after: int | None = None,
    ) -> None:
        """初期化。"""
        message = f"外部サービスエラー ({service}): {error_type} - {error_message}"
        super().__init__(
            message,
            {
                "service": service,
                "error_type": error_type,
                "error_message": error_message,
                "retry_after": retry_after,
            },
        )


class ValidationError(DomainException):
    """検証エラー。"""

    def __init__(self, message: str) -> None:
        """初期化。"""
        super().__init__(message)
