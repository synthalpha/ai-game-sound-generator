"""
タグ管理コントローラーモジュール。

このモジュールでは、タグ管理に関するコントローラーを実装します。
"""

from typing import Any

from src.adapters.controllers.base import HttpController
from src.entities.tag import TagCategory
from src.usecases.base import UseCaseInputPort, UseCaseOutputPort


class CreateTagPresetInputData(UseCaseInputPort):
    """タグプリセット作成入力データ。"""

    def __init__(
        self,
        name: str,
        description: str,
        tags: dict[str, list[str]],
    ) -> None:
        """初期化。"""
        self.name = name
        self.description = description
        self.tags = tags


class CreateTagPresetOutputData(UseCaseOutputPort):
    """タグプリセット作成出力データ。"""

    def __init__(
        self,
        preset_id: str,
        name: str,
        description: str,
        tags: dict[str, list[str]],
    ) -> None:
        """初期化。"""
        self.preset_id = preset_id
        self.name = name
        self.description = description
        self.tags = tags


class CreateTagPresetController(
    HttpController[CreateTagPresetInputData, CreateTagPresetOutputData]
):
    """タグプリセット作成コントローラー。"""

    def _parse_request(self, request_data: dict[str, Any]) -> CreateTagPresetInputData:
        """リクエストデータを入力データに変換。"""
        # 必須フィールドのバリデーション
        if "name" not in request_data:
            raise ValueError("プリセット名は必須です")

        name = request_data["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("プリセット名は空でない文字列である必要があります")

        description = request_data.get("description", "")
        if not isinstance(description, str):
            raise ValueError("説明は文字列である必要があります")

        # タグのバリデーション
        tags = request_data.get("tags", {})
        if not isinstance(tags, dict):
            raise ValueError("タグは辞書形式である必要があります")

        # カテゴリの検証
        valid_categories = {
            "mood": TagCategory.MOOD,
            "genre": TagCategory.GENRE,
            "instrument": TagCategory.INSTRUMENT,
            "tempo": TagCategory.TEMPO,
            "scene": TagCategory.SCENE,
        }
        for category_name, tag_list in tags.items():
            if category_name.lower() not in valid_categories:
                raise ValueError(f"無効なカテゴリ: {category_name}")

            if not isinstance(tag_list, list):
                raise ValueError(f"カテゴリ {category_name} のタグはリストである必要があります")

            for tag in tag_list:
                if not isinstance(tag, str):
                    raise ValueError(f"タグは文字列である必要があります: {tag}")

        return CreateTagPresetInputData(
            name=name,
            description=description,
            tags=tags,
        )


class GetTagPresetsInputData(UseCaseInputPort):
    """タグプリセット取得入力データ。"""

    def __init__(self, limit: int = 10, offset: int = 0) -> None:
        """初期化。"""
        self.limit = limit
        self.offset = offset


class GetTagPresetsOutputData(UseCaseOutputPort):
    """タグプリセット取得出力データ。"""

    def __init__(
        self,
        items: list[dict[str, Any]],
        total: int,
        limit: int,
        offset: int,
    ) -> None:
        """初期化。"""
        self.items = items
        self.total = total
        self.limit = limit
        self.offset = offset


class GetTagPresetsController(HttpController[GetTagPresetsInputData, GetTagPresetsOutputData]):
    """タグプリセット取得コントローラー。"""

    def _parse_request(self, request_data: dict[str, Any]) -> GetTagPresetsInputData:
        """リクエストデータを入力データに変換。"""
        limit = request_data.get("limit", 10)
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("取得件数は正の整数である必要があります")

        offset = request_data.get("offset", 0)
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("オフセットは非負整数である必要があります")

        return GetTagPresetsInputData(limit=limit, offset=offset)


class RecommendTagsInputData(UseCaseInputPort):
    """タグ推奨入力データ。"""

    def __init__(
        self,
        prompt: str,
        existing_tags: list[str] | None = None,
    ) -> None:
        """初期化。"""
        self.prompt = prompt
        self.existing_tags = existing_tags or []


class RecommendTagsOutputData(UseCaseOutputPort):
    """タグ推奨出力データ。"""

    def __init__(
        self,
        recommended_tags: dict[str, list[str]],
        confidence_scores: dict[str, float],
    ) -> None:
        """初期化。"""
        self.recommended_tags = recommended_tags
        self.confidence_scores = confidence_scores


class RecommendTagsController(HttpController[RecommendTagsInputData, RecommendTagsOutputData]):
    """タグ推奨コントローラー。"""

    def _parse_request(self, request_data: dict[str, Any]) -> RecommendTagsInputData:
        """リクエストデータを入力データに変換。"""
        if "prompt" not in request_data:
            raise ValueError("プロンプトは必須です")

        prompt = request_data["prompt"]
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("プロンプトは空でない文字列である必要があります")

        existing_tags = request_data.get("existing_tags", [])
        if not isinstance(existing_tags, list):
            raise ValueError("既存タグはリストである必要があります")

        return RecommendTagsInputData(
            prompt=prompt,
            existing_tags=existing_tags,
        )
