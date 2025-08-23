# アーキテクチャ設計書

## 概要

AI Game Sound Generatorは、クリーンアーキテクチャ（ヘキサゴナルアーキテクチャ）を採用しています。
これにより、ビジネスロジックを外部の技術詳細から分離し、テスタブルで保守性の高いコードベースを実現します。

## アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────┐
│                          UI Layer                           │
│                    (Streamlit / FastAPI)                    │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                       Controllers                           │
│                  (入力の制御・検証)                          │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                        Use Cases                            │
│                  (アプリケーションロジック)                  │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                         Entities                            │
│                    (ドメインモデル)                         │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                         Adapters                            │
│            (Gateways / Repositories / Presenters)           │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                    External Services                        │
│              (ElevenLabs API / Database / etc)              │
└─────────────────────────────────────────────────────────────┘
```

## ディレクトリ構造

```
src/
├── main.py               # FastAPIエントリーポイント
│
├── entities/             # ドメインモデル層
│   ├── audio.py         # 音楽データモデル
│   ├── tag.py           # タグモデル
│   └── generation.py    # 生成リクエスト/レスポンスモデル
│
├── usecases/            # ユースケース層
│   ├── common/          # インターフェース定義
│   │   ├── audio_generator_gateway.py
│   │   ├── audio_repository.py
│   │   └── presenter.py
│   └── audio_generation/ # 音楽生成ユースケース
│       └── generate_audio.py
│
├── adapters/            # アダプター層
│   ├── gateways/        # 外部API接続
│   │   └── elevenlabs.py
│   ├── repositories/    # データ永続化
│   │   └── file_audio.py
│   ├── presenters/      # 出力整形
│   │   └── json_presenter.py
│   └── mappers/         # データ変換
│       └── audio_mapper.py
│
├── controllers/         # コントローラー層
│   ├── api/            # FastAPI コントローラー
│   │   └── audio_controller.py
│   └── streamlit/      # Streamlit コントローラー
│       └── generator_controller.py
│
├── app/                 # UI層（Streamlit）
│   ├── main.py         # Streamlitエントリーポイント
│   ├── components/     # UIコンポーネント
│   │   └── tag_selector.py
│   └── config/         # UI設定
│       └── settings.py
│
├── di_container/        # 依存性注入
│   └── container.py
│
└── config/             # アプリケーション設定
    └── settings.py
```

## 層の責務

### 1. Entities（エンティティ層）

- **責務**: ビジネスルールとドメインロジックを含む
- **依存**: なし（最も内側の層）
- **例**: `Audio`, `Tag`, `GenerationRequest`

### 2. Use Cases（ユースケース層）

- **責務**: アプリケーション固有のビジネスルールを実装
- **依存**: Entities層のみ
- **例**: `GenerateAudioUseCase`, `SaveAudioHistoryUseCase`

### 3. Adapters（アダプター層）

- **責務**: 外部システムとの接続を実装
- **依存**: Use Cases層とEntities層
- **サブ層**:
  - **Gateways**: 外部API接続（ElevenLabs API等）
  - **Repositories**: データ永続化（ファイル、DB等）
  - **Presenters**: 出力データの整形
  - **Mappers**: データ形式の変換

### 4. Controllers（コントローラー層）

- **責務**: 入力の受付、検証、ユースケース呼び出し
- **依存**: Use Cases層、Adapters層
- **例**: `StreamlitGeneratorController`, `FastAPIAudioController`

### 5. UI/API層

- **責務**: ユーザーインターフェースの提供
- **依存**: Controllers層
- **実装**: 
  - **Streamlit** (`src/app/main.py`): デモUI
  - **FastAPI** (`src/main.py`): REST API

## データフロー例

### 音楽生成のフロー

1. **UI層** (Streamlit)
   - ユーザーがタグを選択
   - 生成ボタンをクリック

2. **Controller層**
   ```python
   request = GenerationRequest(mood_tags, genre_tags, instrument_tags)
   controller.generate_audio(request)
   ```

3. **UseCase層**
   ```python
   class GenerateAudioUseCase:
       def execute(self, request: GenerationRequest) -> Audio:
           prompt = self._build_prompt(request)
           audio = self._gateway.generate(prompt)
           self._repository.save(audio)
           return audio
   ```

4. **Adapter層**
   - Gateway: ElevenLabs APIを呼び出し
   - Repository: 生成された音楽をファイルに保存
   - Presenter: レスポンスをJSON形式に整形

5. **UI層**
   - 生成結果を表示
   - 音楽プレイヤーで再生

## 依存性注入（DI）

dependency-injectorを使用して依存関係を管理：

```python
# di_container/container.py
class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    # Gateways
    audio_gateway = providers.Singleton(
        ElevenLabs,
        api_key=config.elevenlabs.api_key,
    )
    
    # Repositories
    audio_repository = providers.Singleton(
        FileAudioRepository,
        output_dir=config.storage.output_dir,
    )
    
    # Use Cases
    generate_audio_usecase = providers.Factory(
        GenerateAudioUseCase,
        gateway=audio_gateway,
        repository=audio_repository,
    )
    
    # Controllers
    generator_controller = providers.Factory(
        StreamlitGeneratorController,
        usecase=generate_audio_usecase,
    )
```

## テスト戦略

### 単体テスト

各層を独立してテスト：

```python
# tests/unit/test_generate_audio_usecase.py
def test_generate_audio_with_valid_tags():
    mock_gateway = Mock(spec=AudioGeneratorGateway)
    mock_repository = Mock(spec=AudioRepository)
    
    usecase = GenerateAudioUseCase(mock_gateway, mock_repository)
    result = usecase.execute(request)
    
    assert result.status == "success"
```

### 統合テスト

複数の層を組み合わせてテスト：

```python
# tests/integration/test_audio_generation_flow.py
def test_full_generation_flow():
    container = Container()
    controller = container.generator_controller()
    
    response = controller.generate_audio(request)
    
    assert response.audio_path.exists()
```

## 拡張ポイント

### 新しい音楽生成APIの追加

1. `adapters/gateways/`に新しいGatewayクラスを作成
2. `AudioGeneratorGateway`インターフェースを実装
3. DIコンテナで切り替え可能に設定

### 新しいストレージの追加

1. `adapters/repositories/`に新しいRepositoryクラスを作成
2. `AudioRepository`インターフェースを実装
3. DIコンテナで設定を変更

### 新しいUIの追加

1. `controllers/`に新しいControllerを作成
2. 対応するUI層のコードを実装
3. 既存のUseCaseを再利用

## セキュリティ考慮事項

- APIキーは環境変数で管理
- 入力値のバリデーションはController層で実施
- ファイルアップロードのサイズ制限
- レート制限の実装

## パフォーマンス考慮事項

- 音楽生成は非同期処理で実装
- キャッシュ機構の導入（Redis等）
- CDNを利用した音楽ファイル配信
- データベースインデックスの最適化

## 参考資料

- [Azure OpenAI を活用したアプリケーションに Clean Architecture を導入してみた (Insight Edge Tech Blog)](https://techblog.insightedge.jp/entry/aoai-app-clean-architecture)
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [dependency-injector Documentation](https://python-dependency-injector.ets-labs.org/)

---

このアーキテクチャ設計により、保守性、テスタビリティ、拡張性の高いシステムを実現します。