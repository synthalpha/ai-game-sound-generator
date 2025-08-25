"""
Streamlitアプリケーションのエントリーポイント。

音楽生成UIのメインアプリケーションです。
"""

import asyncio
import os

import streamlit as st
from dotenv import load_dotenv

from src.adapters.gateways.elevenlabs import ElevenLabs
from src.adapters.repositories.prompt_repository import PromptRepository
from src.adapters.repositories.tag_repository import TagRepository
from src.di_container.config import ElevenLabsConfig
from src.entities.music_generation import MusicGenerationRequest
from src.entities.prompt import PromptType
from src.usecases.prompt_generation.generate_prompt import GeneratePromptUseCase

# 環境変数を読み込み
load_dotenv()


def configure_page() -> None:
    """ページ設定を構成。"""
    st.set_page_config(
        page_title="AI Game Sound Generator",
        page_icon="🎮",
        layout="wide",
    )


def main() -> None:
    """メインアプリケーション。"""
    configure_page()

    # タイトル
    st.title("🎮 AI Game Sound Generator")
    st.markdown("### Tokyo Game Show 2025 Demo")
    st.divider()

    # リポジトリ初期化
    tag_repo = TagRepository()
    prompt_repo = PromptRepository()
    prompt_generator = GeneratePromptUseCase(tag_repo, prompt_repo)

    # 2カラムレイアウト
    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown("### 🎵 音楽生成設定")

        # タグ選択
        selected_tags = []
        categories = tag_repo.get_all_categories()

        for category in categories:
            st.markdown(f"**{category.display_name}**")
            tags = tag_repo.get_tags_by_category(category.id)

            if tags:
                tag_names = [tag.value.name_ja or tag.value.name for tag in tags]
                tag_ids = [f"{category.id}_{tag.value.name.lower()}" for tag in tags]

                if category.isExclusive:
                    # ラジオボタン（排他的選択）
                    selected = st.radio(
                        f"{category.display_name}を選択",
                        options=tag_ids,
                        format_func=lambda x, names=tag_names, ids=tag_ids: names[ids.index(x)],
                        key=f"radio_{category.id}",
                        label_visibility="collapsed",
                    )
                    if selected:
                        selected_tags.append(selected)
                else:
                    # マルチセレクト（複数選択）
                    selected = st.multiselect(
                        f"{category.display_name}を選択",
                        options=tag_ids,
                        format_func=lambda x, names=tag_names, ids=tag_ids: names[ids.index(x)],
                        key=f"multi_{category.id}",
                        max_selections=category.maxSelections,
                        label_visibility="collapsed",
                    )
                    selected_tags.extend(selected)

        # 生成設定
        st.markdown("#### ⚙️ 詳細設定")
        duration = st.slider(
            "音楽の長さ（秒）",
            min_value=5,
            max_value=30,
            value=10,
            step=5,
        )

        # 生成ボタン
        generate_button = st.button(
            "🎼 音楽を生成",
            type="primary",
            use_container_width=True,
            disabled=len(selected_tags) == 0,
        )

    with col2:
        st.markdown("### 🎧 生成結果")

        if generate_button and selected_tags:
            # プロンプト生成
            with st.spinner("プロンプトを生成中..."):
                prompt = prompt_generator.execute(
                    selected_tags,
                    prompt_type=PromptType.MUSIC,
                    duration_seconds=duration,
                )

            # プロンプト表示
            st.markdown("#### 生成プロンプト")
            st.code(prompt.text, language="text")

            # 音楽生成
            with st.spinner(f"音楽を生成中...（約{duration}秒）"):
                try:
                    # ElevenLabs API呼び出し
                    api_key = os.getenv("ELEVENLABS_API_KEY")
                    if not api_key:
                        st.error("APIキーが設定されていません。")
                        st.stop()

                    config = ElevenLabsConfig(api_key=api_key)
                    elevenlabs = ElevenLabs(config)

                    request = MusicGenerationRequest(
                        prompt=prompt.text,
                        duration_seconds=duration,
                    )

                    # 非同期実行
                    async def generate():
                        return await elevenlabs.compose_music(request, output_format="mp3")

                    music_file = asyncio.run(generate())

                    st.success("✅ 音楽生成が完了しました！")

                    # 音楽プレイヤー
                    st.audio(music_file.data, format="audio/mp3")

                    # ダウンロードボタン
                    st.download_button(
                        "💾 ダウンロード",
                        data=music_file.data,
                        file_name=music_file.file_name,
                        mime="audio/mp3",
                    )

                    # 生成情報
                    st.info(f"""
                    - ファイル名: {music_file.file_name}
                    - サイズ: {music_file.file_size_bytes:,} bytes
                    - 長さ: {music_file.duration_seconds}秒
                    """)

                except Exception as e:
                    st.error(f"音楽生成に失敗しました: {e}")
        else:
            st.info("👈 左側でタグを選択して、音楽を生成してください")


if __name__ == "__main__":
    main()
