"""
音楽生成パラメータ管理。

音楽生成のパラメータを管理し、プリセットや履歴を扱います。
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.entities.exceptions import ValidationError
from src.entities.music_generation import MusicGenerationRequest


@dataclass
class GenerationParameters:
    """生成パラメータ。"""

    name: str
    description: str | None = None
    prompt_template: str | None = None
    duration_seconds: int = 30
    style: str | None = None
    mood: str | None = None
    tempo: str | None = None
    instrument_tags: list[str] | None = None
    scene_tags: list[str] | None = None
    custom_parameters: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換。"""
        data = asdict(self)
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationParameters":
        """辞書から生成。"""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class ParameterPreset:
    """パラメータプリセット。"""

    def __init__(self, preset_id: str, parameters: GenerationParameters) -> None:
        """初期化。

        Args:
            preset_id: プリセットID
            parameters: パラメータ
        """
        self.id = preset_id
        self.parameters = parameters
        self.usage_count = 0
        self.last_used_at: datetime | None = None

    def use(self) -> GenerationParameters:
        """プリセットを使用。

        Returns:
            パラメータのコピー
        """
        self.usage_count += 1
        self.last_used_at = datetime.now()
        return GenerationParameters(**asdict(self.parameters))


class ParameterManager:
    """パラメータマネージャー。

    生成パラメータのプリセット管理と履歴管理を行います。
    """

    def __init__(self, storage_path: str | Path | None = None) -> None:
        """初期化。

        Args:
            storage_path: ストレージパス（オプション）
        """
        self._storage_path = Path(storage_path) if storage_path else None
        self._presets: dict[str, ParameterPreset] = {}
        self._history: list[GenerationParameters] = []
        self._logger = logging.getLogger(__name__)

        # デフォルトプリセットを登録
        self._register_default_presets()

        # ストレージから読み込み
        if self._storage_path:
            self._load_from_storage()

    def add_preset(
        self,
        preset_id: str,
        parameters: GenerationParameters,
    ) -> ParameterPreset:
        """プリセットを追加。

        Args:
            preset_id: プリセットID
            parameters: パラメータ

        Returns:
            追加されたプリセット

        Raises:
            ValidationError: 既に存在するIDの場合
        """
        if preset_id in self._presets:
            raise ValidationError(f"プリセットID '{preset_id}' は既に存在します")

        preset = ParameterPreset(preset_id, parameters)
        self._presets[preset_id] = preset

        self._logger.info(f"プリセットを追加: {preset_id}")
        self._save_to_storage()

        return preset

    def get_preset(self, preset_id: str) -> ParameterPreset | None:
        """プリセットを取得。

        Args:
            preset_id: プリセットID

        Returns:
            プリセット（存在しない場合はNone）
        """
        return self._presets.get(preset_id)

    def list_presets(self) -> list[ParameterPreset]:
        """プリセット一覧を取得。

        Returns:
            プリセットのリスト
        """
        return list(self._presets.values())

    def use_preset(self, preset_id: str) -> GenerationParameters:
        """プリセットを使用。

        Args:
            preset_id: プリセットID

        Returns:
            パラメータ

        Raises:
            ValidationError: プリセットが存在しない場合
        """
        preset = self.get_preset(preset_id)
        if not preset:
            raise ValidationError(f"プリセット '{preset_id}' が見つかりません")

        parameters = preset.use()
        self._add_to_history(parameters)

        return parameters

    def create_from_request(
        self,
        request: MusicGenerationRequest,
        name: str,
    ) -> GenerationParameters:
        """リクエストからパラメータを作成。

        Args:
            request: 音楽生成リクエスト
            name: パラメータ名

        Returns:
            生成パラメータ
        """
        parameters = GenerationParameters(
            name=name,
            prompt_template=request.prompt,
            duration_seconds=request.duration_seconds,
            style=request.style,
            mood=request.mood,
            tempo=request.tempo,
            created_at=datetime.now(),
        )

        self._add_to_history(parameters)
        return parameters

    def get_history(self, limit: int = 100) -> list[GenerationParameters]:
        """履歴を取得。

        Args:
            limit: 取得件数の上限

        Returns:
            パラメータのリスト（新しい順）
        """
        return self._history[:limit]

    def clear_history(self) -> None:
        """履歴をクリア。"""
        self._history.clear()
        self._logger.info("履歴をクリアしました")

    def _add_to_history(self, parameters: GenerationParameters) -> None:
        """履歴に追加。

        Args:
            parameters: パラメータ
        """
        self._history.insert(0, parameters)

        # 履歴の上限を1000件に制限
        if len(self._history) > 1000:
            self._history = self._history[:1000]

    def _register_default_presets(self) -> None:
        """デフォルトプリセットを登録。"""
        # RPGバトル
        self._presets["rpg_battle"] = ParameterPreset(
            "rpg_battle",
            GenerationParameters(
                name="RPGバトル",
                description="RPGゲームのバトルシーン用",
                prompt_template="epic orchestral battle music for RPG game",
                duration_seconds=60,
                style="cinematic",
                mood="epic",
                tempo="fast",
                scene_tags=["battle", "boss"],
                instrument_tags=["orchestra", "drums"],
            ),
        )

        # パズルゲーム
        self._presets["puzzle_game"] = ParameterPreset(
            "puzzle_game",
            GenerationParameters(
                name="パズルゲーム",
                description="パズルゲーム用の軽快な音楽",
                prompt_template="cheerful and relaxing puzzle game music",
                duration_seconds=90,
                style="ambient",
                mood="happy",
                tempo="medium",
                scene_tags=["puzzle", "thinking"],
                instrument_tags=["piano", "synth"],
            ),
        )

        # タイトル画面
        self._presets["title_screen"] = ParameterPreset(
            "title_screen",
            GenerationParameters(
                name="タイトル画面",
                description="ゲームのタイトル画面用",
                prompt_template="majestic and mysterious title screen music",
                duration_seconds=45,
                style="cinematic",
                mood="mysterious",
                tempo="slow",
                scene_tags=["title", "menu"],
                instrument_tags=["orchestra", "choir"],
            ),
        )

        # アクションゲーム
        self._presets["action_game"] = ParameterPreset(
            "action_game",
            GenerationParameters(
                name="アクションゲーム",
                description="高速アクションゲーム用",
                prompt_template="intense electronic action game music",
                duration_seconds=60,
                style="electronic",
                mood="energetic",
                tempo="fast",
                scene_tags=["action", "chase"],
                instrument_tags=["synth", "drums", "bass"],
            ),
        )

    def _load_from_storage(self) -> None:
        """ストレージから読み込み。"""
        if not self._storage_path or not self._storage_path.exists():
            return

        # プリセットファイル
        presets_file = self._storage_path / "presets.json"
        if presets_file.exists():
            try:
                with open(presets_file, encoding="utf-8") as f:
                    data = json.load(f)
                    for preset_id, preset_data in data.items():
                        params = GenerationParameters.from_dict(preset_data["parameters"])
                        preset = ParameterPreset(preset_id, params)
                        preset.usage_count = preset_data.get("usage_count", 0)
                        if "last_used_at" in preset_data:
                            preset.last_used_at = datetime.fromisoformat(
                                preset_data["last_used_at"]
                            )
                        self._presets[preset_id] = preset
                self._logger.info(f"プリセットを読み込みました: {len(self._presets)}件")
            except Exception as e:
                self._logger.error(f"プリセットの読み込みエラー: {e}")

        # 履歴ファイル
        history_file = self._storage_path / "history.json"
        if history_file.exists():
            try:
                with open(history_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self._history = [GenerationParameters.from_dict(item) for item in data]
                self._logger.info(f"履歴を読み込みました: {len(self._history)}件")
            except Exception as e:
                self._logger.error(f"履歴の読み込みエラー: {e}")

    def _save_to_storage(self) -> None:
        """ストレージに保存。"""
        if not self._storage_path:
            return

        self._storage_path.mkdir(parents=True, exist_ok=True)

        # プリセットを保存
        presets_file = self._storage_path / "presets.json"
        try:
            presets_data = {}
            for preset_id, preset in self._presets.items():
                presets_data[preset_id] = {
                    "parameters": preset.parameters.to_dict(),
                    "usage_count": preset.usage_count,
                    "last_used_at": preset.last_used_at.isoformat()
                    if preset.last_used_at
                    else None,
                }
            with open(presets_file, "w", encoding="utf-8") as f:
                json.dump(presets_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._logger.error(f"プリセットの保存エラー: {e}")

        # 履歴を保存
        history_file = self._storage_path / "history.json"
        try:
            history_data = [params.to_dict() for params in self._history[:100]]  # 最新100件のみ
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._logger.error(f"履歴の保存エラー: {e}")
