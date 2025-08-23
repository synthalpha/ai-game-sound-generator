# AI Game Sound Generator

ゲームクリエイター向けの革新的なオーディオ生成サービス。AIを活用して、ゲームの雰囲気やシーンに最適な音楽・効果音を自動生成します。

Tokyo Game Show 2025展示用プロトタイプ

## 特徴

- **タグベース生成**: ジャンル、雰囲気、シーンなどのタグを選択するだけで音楽を生成
- **リアルタイムプレビュー**: 生成した音楽を即座に確認
- **カスタマイズ可能**: テンポ、楽器、ムードなどを細かく調整
- **高品質出力**: ElevenLabs APIを活用した高品質な音声生成

## 必要環境

- Docker Desktop
- Visual Studio Code（推奨）
- Git

## セットアップ

### 推奨: VS Code Dev Containers

1. リポジトリをクローン
```bash
git clone https://github.com/synthalpha/ai-game-sound-generator.git
cd ai-game-sound-generator
```

2. 環境変数を設定
```bash
cp .env.example .env
# .envファイルを編集してElevenLabs APIキーなどを設定
```

3. VS Codeで開く
```bash
code .
```

4. 「Reopen in Container」を選択（自動プロンプトまたは左下の緑アイコンから）

### 代替: Docker Compose

```bash
# リポジトリをクローン
git clone https://github.com/synthalpha/ai-game-sound-generator.git
cd ai-game-sound-generator

# 環境変数を設定
cp .env.example .env

# Dockerコンテナを起動
docker compose up -d
```

## 使い方

### アプリケーションへのアクセス

- **Streamlit UI**: http://localhost:8501
- **FastAPI**: http://localhost:8000

### 基本的な使用フロー

1. Streamlit UIにアクセス
2. 生成したい音楽のタグを選択
3. 「生成」ボタンをクリック
4. 生成された音楽をプレビュー
5. 必要に応じてダウンロード

## プロジェクト構造

```
.
├── src/
│   ├── app/              # Streamlit UI
│   ├── controllers/      # APIコントローラー
│   ├── entities/         # ドメインモデル
│   ├── usecases/        # ビジネスロジック
│   └── adapters/        # 外部サービス連携
├── tests/               # テストコード
├── docs/                # ドキュメント
├── docker-compose.yml   # Docker設定
└── Makefile            # 開発タスク自動化
```

## 開発

詳細な開発手順は[開発ガイド](https://github.com/synthalpha/ai-game-sound-generator/discussions/22)を参照してください。

### クイックスタート（Dev Container内）

```bash
# 開発サーバー起動（Streamlit）
make dev

# FastAPI起動
make api

# テスト実行
make test

# コード品質チェック
make check

# 自動修正
make fix
```

## ドキュメント

- [開発ガイド](https://github.com/synthalpha/ai-game-sound-generator/discussions/22) - 環境構築と開発フロー
- [アーキテクチャ設計](https://github.com/synthalpha/ai-game-sound-generator/discussions/33) - システム設計の詳細
- [コーディング規約](https://github.com/synthalpha/ai-game-sound-generator/discussions/34) - コードスタイルガイド
