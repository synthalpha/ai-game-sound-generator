"""Streamlitアプリケーションのエントリーポイント"""

import streamlit as st

from app.components.tag_selector import render_tag_selector
from app.config.settings import apply_custom_css, configure_page
from controllers.streamlit.generator_controller import (
    GenerationRequest,
    StreamlitGeneratorController,
)

# ページ設定
configure_page()
apply_custom_css()


def main():
    """メインアプリケーション関数"""
    # ヘッダー
    st.title("🎮 AI Game Sound Generator")
    st.markdown("### Tokyo Game Show 2025 Demo")
    st.divider()

    # コントローラー初期化
    controller = StreamlitGeneratorController()

    # レイアウト用のカラム作成
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### 🎵 音楽生成設定")

        # タグ選択コンポーネント
        tags = render_tag_selector()

        # 生成ボタン
        generate_button = st.button(
            "🎼 音楽を生成",
            type="primary",
            use_container_width=True,
        )

    with col2:
        st.markdown("### 🎧 生成結果")

        # 結果コンテナ
        result_container = st.container()

        with result_container:
            if generate_button and any([tags["mood"], tags["genre"], tags["instrument"]]):
                # 生成リクエスト作成
                request = GenerationRequest(
                    mood_tags=tags["mood"],
                    genre_tags=tags["genre"],
                    instrument_tags=tags["instrument"],
                    tempo=tags.get("tempo"),
                )

                # 進捗表示
                with st.spinner("音楽を生成中... (約30秒)"):
                    progress_bar = st.progress(0)

                    # 音楽生成
                    response = controller.generate_audio(request)

                    # 進捗更新
                    for i in range(100):
                        progress_bar.progress(i + 1)

                # 結果表示
                if response.success:
                    st.success("✅ 生成完了！")

                    # プロンプト表示
                    st.markdown("#### 使用プロンプト")
                    st.code(response.prompt, language="text")

                    # 音声プレイヤー（プレースホルダー）
                    st.markdown("#### 生成された音楽")
                    st.info("🎵 音声プレイヤーがここに表示されます")

                    # ダウンロードボタン
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.button(
                            "💾 ダウンロード",
                            use_container_width=True,
                        )
                    with col_dl2:
                        if st.button(
                            "📚 履歴に保存",
                            use_container_width=True,
                        ):
                            controller.save_to_history(response)
                            st.toast("履歴に保存しました", icon="✅")

                    # 生成情報
                    st.markdown("#### 生成情報")
                    st.markdown(f"- 生成時間: {response.generation_time:.1f}秒")
                    st.markdown(f"- ファイル: {response.audio_path}")

                else:
                    st.error(f"❌ 生成失敗: {response.error_message}")

            elif generate_button:
                st.warning("⚠️ タグを選択してください")
            else:
                st.info("👈 左側でタグを選択して、音楽を生成してください")

    # 履歴セクション
    with st.expander("📜 生成履歴", expanded=False):
        history = controller.get_history()
        if history:
            for i, item in enumerate(reversed(history), 1):
                st.markdown(f"**#{i}** - {item['prompt']}")
                st.caption(f"生成時間: {item['generation_time']:.1f}秒")
        else:
            st.info("履歴がありません")


if __name__ == "__main__":
    main()
