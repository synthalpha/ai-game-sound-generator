.PHONY: help install dev-install setup test lint format check run clean build docker-up docker-down

# デフォルトターゲット
.DEFAULT_GOAL := help

# uvのパスを設定
UV := $(HOME)/.local/bin/uv

# ヘルプ表示
help: ## このヘルプメッセージを表示
	@echo "使用可能なコマンド:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# 環境セットアップ
install: ## 本番用依存関係をインストール
	$(UV) sync

dev-install: ## 開発用依存関係を含めてインストール
	$(UV) sync --all-extras

setup: dev-install ## 初期セットアップ（依存関係インストール + Git hooks設定）
	lefthook install
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .envファイルを作成しました"; \
	fi
	@echo "✅ セットアップ完了！.envファイルを編集してAPIキーを設定してください"

# コード品質
lint: ## Ruffでコードをチェック
	$(UV) run ruff check .

format: ## Ruffでコードをフォーマット
	$(UV) run ruff format .

check: ## lintとformatをチェックモードで実行
	$(UV) run ruff check .
	$(UV) run ruff format --check .

fix: ## 自動修正可能な問題を修正
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

# テスト
test: ## テストを実行
	$(UV) run pytest

test-verbose: ## テストを詳細モードで実行
	$(UV) run pytest -v

test-cov: ## カバレッジ付きでテストを実行
	$(UV) run pytest --cov=src --cov-report=term-missing --cov-report=html

test-watch: ## ファイル変更を監視してテストを自動実行
	$(UV) run pytest-watch

# 開発サーバー
run: ## 開発サーバーを起動（FastAPI）
	$(UV) run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## 本番モードでサーバーを起動（FastAPI）
	$(UV) run uvicorn src.main:app --host 0.0.0.0 --port 8000

streamlit: ## Streamlit UIを起動
	$(UV) run streamlit run src/app/main.py --server.port 8501 --server.address 0.0.0.0

streamlit-dev: ## Streamlit UIを開発モードで起動
	$(UV) run streamlit run src/app/main.py --server.port 8501 --server.address 0.0.0.0 --server.runOnSave true

# Docker関連
docker-build: ## Dockerイメージをビルド
	docker-compose build

docker-up: ## Docker Composeで起動
	docker-compose up -d

docker-down: ## Docker Composeで停止
	docker-compose down

docker-dev: ## 開発環境でDocker起動（フォアグラウンド）
	docker-compose up

docker-api: ## DockerでFastAPIを起動
	docker-compose up api

docker-streamlit: ## DockerでStreamlitを起動
	docker-compose up streamlit

docker-logs: ## Docker Composeのログを表示
	docker-compose logs -f

docker-exec: ## Dockerコンテナに入る
	docker-compose exec api bash

docker-clean: ## Dockerリソースをクリーンアップ
	docker-compose down -v
	docker system prune -f

# クリーンアップ
clean: ## 生成ファイルとキャッシュを削除
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ 2>/dev/null || true

clean-all: clean ## すべての生成ファイル（.venvを含む）を削除
	rm -rf .venv/
	rm -rf generated_audio/
	rm -f uv.lock

# Git関連
commit: ## 変更をコミット（自動でlint/format実行）
	@read -p "コミットメッセージ (feat/fix/docs/style/refactor/test/chore): " msg; \
	git add -A && git commit -m "$$msg"

# プロジェクト管理
issue-list: ## GitHub Issueを一覧表示
	gh issue list --repo synthalpha/ai-game-sound-generator

pr-list: ## プルリクエストを一覧表示
	gh pr list --repo synthalpha/ai-game-sound-generator

# 開発ワークフロー
dev: ## 開発環境を起動（Streamlit UI）
	@echo "🚀 Streamlit UIを起動します..."
	$(MAKE) streamlit-dev

api: ## API開発環境を起動（FastAPI）
	@echo "🚀 FastAPI開発サーバーを起動します..."
	$(MAKE) run

ci: ## CI環境で実行するコマンド（lint, format check, test）
	$(MAKE) check
	$(MAKE) test-cov

pre-commit: ## コミット前チェック（手動実行用）
	$(MAKE) fix
	$(MAKE) test

# 情報表示
info: ## プロジェクト情報を表示
	@echo "プロジェクト: AI Game Sound Generator"
	@echo "Python: $$(uv run python --version)"
	@echo "uv: $$(uv --version)"
	@echo "依存関係:"
	@$(UV) pip list