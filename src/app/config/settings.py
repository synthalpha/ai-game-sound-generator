"""Streamlitアプリケーション設定"""

import streamlit as st


def configure_page():
    """Streamlitページ設定を構成"""
    st.set_page_config(
        page_title="AI Game Sound Generator",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://github.com/synthalpha/ai-game-sound-generator",
            "Report a bug": "https://github.com/synthalpha/ai-game-sound-generator/issues",
            "About": "AI-powered game audio generation for Tokyo Game Show 2025",
        },
    )


def apply_custom_css():
    """カスタムCSSスタイルを適用"""
    st.markdown(
        """
        <style>
        /* メインコンテナ */
        .main {
            padding-top: 2rem;
        }

        /* ボタンスタイル */
        .stButton > button {
            width: 100%;
            border-radius: 8px;
            height: 3rem;
            font-weight: 600;
        }

        /* サイドバー */
        .css-1d391kg {
            padding-top: 2rem;
        }

        /* タグ選択 */
        .stMultiSelect {
            margin-bottom: 1rem;
        }

        /* プログレスバー */
        .stProgress > div > div > div > div {
            background-color: #4CAF50;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
