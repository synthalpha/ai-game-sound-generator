"""
音楽エンティティのテスト。

Audioエンティティと関連する値オブジェクトの動作を検証します。
"""

import pytest

from src.entities.audio import (
    Audio,
    AudioCollection,
    AudioDuration,
    AudioFormat,
    AudioQuality,
    AudioStatus,
    Prompt,
)
from src.entities.base import Description, FilePath, Name


class TestAudioDuration:
    """AudioDurationクラスのテスト。"""

    def test_valid_duration(self) -> None:
        """有効な長さのテスト。"""
        duration = AudioDuration(seconds=120)
        assert duration.seconds == 120
        assert duration.minutes == 2.0
        assert duration.milliseconds == 120000
        assert str(duration) == "02:00"

    def test_invalid_duration_too_short(self) -> None:
        """短すぎる長さのテスト。"""
        with pytest.raises(ValueError, match="音楽の長さは1秒以上にしてください"):
            AudioDuration(seconds=0)

    def test_invalid_duration_too_long(self) -> None:
        """長すぎる長さのテスト。"""
        with pytest.raises(ValueError, match="音楽の長さは300秒以内にしてください"):
            AudioDuration(seconds=301)

    def test_duration_string_format(self) -> None:
        """文字列フォーマットのテスト。"""
        assert str(AudioDuration(seconds=65)) == "01:05"
        assert str(AudioDuration(seconds=299)) == "04:59"  # 最大値近く


class TestAudioQuality:
    """AudioQualityクラスのテスト。"""

    def test_valid_quality(self) -> None:
        """有効な音質設定のテスト。"""
        quality = AudioQuality(bitrate=320, sample_rate=48000)
        assert quality.bitrate == 320
        assert quality.sample_rate == 48000

    def test_invalid_bitrate(self) -> None:
        """無効なビットレートのテスト。"""
        with pytest.raises(ValueError, match="ビットレートは"):
            AudioQuality(bitrate=64, sample_rate=44100)

    def test_invalid_sample_rate(self) -> None:
        """無効なサンプルレートのテスト。"""
        with pytest.raises(ValueError, match="サンプルレートは"):
            AudioQuality(bitrate=320, sample_rate=22050)


class TestPrompt:
    """Promptクラスのテスト。"""

    def test_valid_prompt(self) -> None:
        """有効なプロンプトのテスト。"""
        prompt = Prompt(text="Epic battle music", tags=["epic", "battle"])
        assert prompt.text == "Epic battle music"
        assert prompt.tags == ["epic", "battle"]
        assert str(prompt) == "Epic battle music"

    def test_empty_prompt(self) -> None:
        """空のプロンプトのテスト。"""
        with pytest.raises(ValueError, match="プロンプトは空にできません"):
            Prompt(text="", tags=[])

    def test_too_long_prompt(self) -> None:
        """長すぎるプロンプトのテスト。"""
        with pytest.raises(ValueError, match="プロンプトは2000文字以内にしてください"):
            Prompt(text="a" * 2001, tags=[])


class TestAudio:
    """Audioクラスのテスト。"""

    def create_audio(self) -> Audio:
        """テスト用のAudioインスタンスを作成。"""
        return Audio(
            name=Name(value="テスト音楽"),
            description=Description(value="テスト用の音楽"),
            prompt=Prompt(text="Test music", tags=["test"]),
            duration=AudioDuration(seconds=30),
            format=AudioFormat.MP3,
            quality=AudioQuality(bitrate=320, sample_rate=48000),
        )

    def test_audio_creation(self) -> None:
        """Audio作成テスト。"""
        audio = self.create_audio()
        assert audio.status == AudioStatus.PENDING
        assert audio.file_path is None
        assert audio.generated_at is None
        assert audio.error_message is None

    def test_start_generation(self) -> None:
        """生成開始テスト。"""
        audio = self.create_audio()
        audio.start_generation()

        assert audio.status == AudioStatus.GENERATING
        assert audio.is_in_progress

    def test_start_generation_invalid_status(self) -> None:
        """無効なステータスからの生成開始テスト。"""
        audio = self.create_audio()
        audio.status = AudioStatus.COMPLETED

        with pytest.raises(ValueError, match="生成を開始できるのはPENDINGステータスのみです"):
            audio.start_generation()

    def test_complete_generation(self) -> None:
        """生成完了テスト。"""
        audio = self.create_audio()
        audio.start_generation()
        audio.complete_generation(FilePath(value="/path/to/audio.mp3"))

        assert audio.status == AudioStatus.COMPLETED
        assert audio.is_completed
        assert audio.file_path.value == "/path/to/audio.mp3"
        assert audio.generated_at is not None

    def test_fail_generation(self) -> None:
        """生成失敗テスト。"""
        audio = self.create_audio()
        audio.start_generation()
        audio.fail_generation("API error occurred")

        assert audio.status == AudioStatus.FAILED
        assert audio.error_message == "API error occurred"
        assert audio.can_retry

    def test_cancel_generation(self) -> None:
        """生成キャンセルテスト。"""
        audio = self.create_audio()
        audio.start_generation()
        audio.cancel_generation()

        assert audio.status == AudioStatus.CANCELLED
        assert audio.can_retry


class TestAudioCollection:
    """AudioCollectionクラスのテスト。"""

    def create_collection(self) -> AudioCollection:
        """テスト用のAudioCollectionインスタンスを作成。"""
        return AudioCollection(
            name=Name(value="テストプレイリスト"),
            description=Description(value="テスト用のプレイリスト"),
        )

    def test_collection_creation(self) -> None:
        """コレクション作成テスト。"""
        collection = self.create_collection()
        assert collection.audios == []
        assert not collection.is_public
        assert collection.audio_count == 0

    def test_add_audio(self) -> None:
        """音楽追加テスト。"""
        collection = self.create_collection()
        audio = self.create_audio()
        collection.add_audio(audio.id)

        assert audio.id in collection.audios
        assert collection.audio_count == 1

    def test_add_duplicate_audio(self) -> None:
        """重複音楽追加テスト。"""
        collection = self.create_collection()
        audio = self.create_audio()
        collection.add_audio(audio.id)

        with pytest.raises(ValueError, match="この音楽は既にコレクションに追加されています"):
            collection.add_audio(audio.id)

    def test_remove_audio(self) -> None:
        """音楽削除テスト。"""
        collection = self.create_collection()
        audio = self.create_audio()
        collection.add_audio(audio.id)
        collection.remove_audio(audio.id)

        assert audio.id not in collection.audios
        assert collection.audio_count == 0

    def test_remove_nonexistent_audio(self) -> None:
        """存在しない音楽の削除テスト。"""
        collection = self.create_collection()
        audio = self.create_audio()

        with pytest.raises(ValueError, match="この音楽はコレクションに存在しません"):
            collection.remove_audio(audio.id)

    def create_audio(self) -> Audio:
        """テスト用のAudioインスタンスを作成。"""
        return Audio(
            name=Name(value="テスト音楽"),
            description=Description(value="テスト用の音楽"),
            prompt=Prompt(text="Test music", tags=["test"]),
            duration=AudioDuration(seconds=30),
            format=AudioFormat.MP3,
            quality=AudioQuality(bitrate=320, sample_rate=48000),
        )
