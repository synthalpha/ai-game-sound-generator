"""Streamlit UI用タグセレクターコンポーネント"""

import streamlit as st


def render_tag_selector() -> dict[str, list[str]]:
    """タグ選択インターフェースをレンダリング

    Returns:
        各カテゴリで選択されたタグを含む辞書
    """
    selected_tags = {}

    # ムードタグ
    st.markdown("#### 🎭 雰囲気")
    selected_tags["mood"] = st.multiselect(
        "雰囲気を選択",
        options=[
            "明るい",
            "暗い",
            "神秘的",
            "荘厳",
            "緊張感",
            "平和",
            "激しい",
            "切ない",
            "楽しい",
            "怖い",
        ],
        max_selections=3,
        help="最大3つまで選択可能",
    )

    # ジャンルタグ
    st.markdown("#### 🎮 ジャンル")
    selected_tags["genre"] = st.multiselect(
        "ゲームジャンルを選択",
        options=[
            "ファンタジー",
            "SF",
            "ホラー",
            "アクション",
            "RPG",
            "パズル",
            "シューティング",
            "アドベンチャー",
            "シミュレーション",
            "レース",
        ],
        max_selections=2,
        help="最大2つまで選択可能",
    )

    # 楽器タグ
    st.markdown("#### 🎹 楽器")
    selected_tags["instrument"] = st.multiselect(
        "楽器を選択",
        options=[
            "オーケストラ",
            "電子音",
            "ピアノ",
            "ギター",
            "ドラム",
            "ストリングス",
            "シンセサイザー",
            "ベース",
            "フルート",
            "バイオリン",
        ],
        max_selections=3,
        help="最大3つまで選択可能",
    )

    # テンポ選択
    st.markdown("#### ⏱️ テンポ")
    selected_tags["tempo"] = st.select_slider(
        "テンポを選択",
        options=["スロー", "ミディアム", "ファスト", "アップテンポ"],
        value="ミディアム",
    )

    # 選択されたタグのサマリー表示
    if any([selected_tags["mood"], selected_tags["genre"], selected_tags["instrument"]]):
        st.markdown("---")
        st.markdown("#### 📋 選択されたタグ")

        all_tags = []
        if selected_tags["mood"]:
            all_tags.extend(selected_tags["mood"])
        if selected_tags["genre"]:
            all_tags.extend(selected_tags["genre"])
        if selected_tags["instrument"]:
            all_tags.extend(selected_tags["instrument"])

        # タグをチップとして表示
        tag_html = " ".join(
            [
                f"<span style='background-color: #4CAF50; color: white; padding: 5px 10px; border-radius: 15px; margin: 2px; display: inline-block;'>{tag}</span>"
                for tag in all_tags
            ]
        )
        st.markdown(tag_html, unsafe_allow_html=True)

    return selected_tags
