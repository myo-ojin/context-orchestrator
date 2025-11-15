# Context Orchestrator

> 開発者のための外部脳システム

**Context Orchestrator**は、プライバシー重視のAI駆動メモリシステムです。あらゆるLLMクライアントでの開発経験を自動的にキャプチャ、整理、想起します。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-48%2F48%20passing-success)](tests/)

[English](README.md) | 日本語

## なぜContext Orchestratorなのか？

開発者として、私たちは常に学習し、トラブルシューティングし、意思決定を行っています。しかし、この知識は以下のような場所で失われがちです：
- 閉じられたターミナルセッション
- 忘れられたAIアシスタントとの会話
- 散在するメモやドキュメント
- 限られたLLMのコンテキストウィンドウ

**Context Orchestratorがこれを解決します**：

✅ **自動メモリ**: CLIの会話を透過的に記録
✅ **インテリジェント整理**: 経験を検索可能なスキーマに分類
✅ **プライバシー第一**: すべての処理をローカルマシンで実行
✅ **汎用的な統合**: Claude CLI、Cursor、VS Code、あらゆるMCPクライアントで動作
✅ **スマート検索**: ハイブリッドベクトル＋キーワード検索で必要なものを正確に発見
✅ **本番環境準備完了**: 包括的なテストスイート（48個のエッジケース、100%合格）

## 機能

### 🧠 自動メモリキャプチャ
- CLIの会話を透過的に記録（Claude、Codex）
- Obsidianボールトノートから会話を抽出
- 手動でメモを取る必要なし

### 📊 スマート整理
メモリをドメイン固有のスキーマに分類：
- **Incident（インシデント）**: バグレポート、エラー、トラブルシューティング手順
- **Snippet（スニペット）**: 使用コンテキスト付きのコード例
- **Decision（決定）**: アーキテクチャの選択とトレードオフ
- **Process（プロセス）**: 思考プロセス、学習、実験

### 🔍 強力な検索
- **ハイブリッド検索**: ベクトル（意味）+ BM25（キーワード）検索
- **クロスエンコーダーリランキング**: LLMベースの関連性スコアリング
- **クエリ属性**: トピック/タイプ/プロジェクトの自動抽出
- **プロジェクトスコープ**: 特定のコードベース内で検索
- **検索ブックマーク**: 頻繁に使用するクエリを保存

### 🏠 プライバシー第一のアーキテクチャ
- **ローカルLLM処理**: 埋め込みと分類をローカルで実行（Ollama）
- **スマートモデルルーティング**: 軽量タスク→ローカル、重いタスク→クラウド（選択可能）
- **テレメトリなし**: すべてのデータがマシン上に留まる
- **エクスポート/インポート**: データを完全にコントロール

### 💾 メモリ階層
人間のメモリパターンを模倣：
- **ワーキングメモリ**: 現在のタスクコンテキスト（8時間）
- **短期メモリ**: 最近の経験（数日〜数週間）
- **長期メモリ**: 重要な知識（永続的）
- **自動統合**: 夜間のメモリ最適化とクリーンアップ

### 🔌 汎用的な統合
あらゆるMCP（Model Context Protocol）互換クライアントで動作：
- Claude CLI
- Cursor IDE
- VS Code拡張機能
- カスタムMCPクライアント

### 🧪 本番環境準備完了の品質
- **48個のエッジケーステスト**: 特殊文字、絵文字、極端な入力（100%合格）
- **負荷テスト**: メモリリーク検出、並行クエリ検証
- **パフォーマンス目標**: 検索<200ms、取り込み<5秒、統合<5分
- **品質指標**: Precision ≥0.65、NDCG ≥0.85
- **リグレッションテスト**: 自動ベースライン比較

## クイックスタート

### 前提条件

- **Python 3.11-3.12**（Python 3.11推奨、3.13以降は未テスト）
- **Ollama**（ローカルLLM処理用）
- **PowerShell**（Windows CLI統合用）または **Bash**（Unix/Linux/Mac用）

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/myo-ojin/llm-brain.git
cd llm-brain

# 仮想環境を作成
python -m venv .venv

# 仮想環境をアクティベート
# Windows（PowerShell）:
.\.venv\Scripts\Activate.ps1
# Windows（コマンドプロンプト）:
.venv\Scripts\activate.bat
# Unix/Linux/Mac:
source .venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt

# セットアップウィザードを実行
python scripts/setup.py
```

**Windows PowerShellユーザーへの注意:**
実行ポリシーエラーが出る場合は、以下を実行してください：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**セットアップウィザードが実行すること:**
- Ollamaのインストールと接続確認
- 必要なモデルのダウンロード確認
- 設定ファイルの作成（`~/.context-orchestrator/config.yaml`）
- データディレクトリの作成
- 基本機能のテスト

### 必要なモデルのダウンロード

Context OrchestratorはローカルLLM処理にOllamaを使用します：

```bash
# https://ollama.ai/ からOllamaをインストール

# Ollamaを起動（まだ起動していない場合）
ollama serve  # 別のターミナルで実行

# 必要なモデルをダウンロード
ollama pull nomic-embed-text    # 埋め込みモデル（274MB、約1分）
ollama pull qwen2.5:7b          # ローカル推論モデル（4.7GB、約5-10分）

# インストール確認
ollama list
```

**期待される出力:**
```
NAME                       ID              SIZE      MODIFIED
nomic-embed-text:latest    0a109f422b47    274 MB    今
qwen2.5:7b                 845dbda0ea48    4.7 GB    今
```

### 設定

セットアップウィザードが `~/.context-orchestrator/config.yaml` を作成します：

```yaml
# データストレージ
data_dir: ~/.context-orchestrator

# Ollama設定
ollama:
  url: http://localhost:11434
  embedding_model: nomic-embed-text
  inference_model: qwen2.5:7b

# 複雑なタスク用のCLI LLM（オプション）
cli:
  command: claude  # または "codex"、空欄でローカルのみ

# 検索パラメータ
search:
  candidate_count: 50
  result_count: 10
  cross_encoder_enabled: true
  cross_encoder_top_k: 3

# メモリ管理
working_memory:
  retention_hours: 8
  auto_consolidate: true

# 統合スケジュール（毎日午前3時）
consolidation:
  schedule: "0 3 * * *"
  auto_enabled: true

# Obsidian統合（オプション）
obsidian_vault_path: C:\Users\username\Documents\ObsidianVault
```

### MCPサーバーを起動

```bash
# MCPサーバーとしてContext Orchestratorを起動
python -m src.main

# またはコンソールエントリーポイントを使用（インストール済みの場合）
context-orchestrator
```

サーバーはstdioモードで実行され、MCPクライアントとJSON-RPCで通信します。

### CLIコマンド

```bash
# システムステータス
python -m src.cli status

# ヘルスチェックと診断
python -m src.cli doctor

# 最近のメモリをリスト表示
python -m src.cli list-recent --limit 20

# 手動メモリ統合
python -m src.cli consolidate

# セッション履歴
python -m src.cli session-history
python -m src.cli session-history --session-id <id>

# メモリのエクスポート/インポート
python -m src.cli export --output backup.json
python -m src.cli import --input backup.json
```

## 仕組み

### 1. キャプチャ
PowerShell/BashラッパーがCLIコマンドを傍受し、MCPプロトコル経由でContext Orchestratorに会話を送信します。

### 2. 処理
- **分類**: ローカルLLMがメモリをスキーマに分類（Incident/Snippet/Decision/Process）
- **チャンク化**: 効率的な処理のためにコンテンツを512トークンのチャンクに分割
- **埋め込み**: ローカルでベクトル埋め込みを生成（nomic-embed-text）
- **インデックス**: ベクトルDB（意味検索）とBM25（キーワード検索）の両方に保存

### 3. 検索
クエリを実行すると：
1. ローカルでクエリ埋め込みを生成
2. 並列検索: ベクトルDB + BM25 → トップ候補
3. クエリ属性を抽出（トピック、タイプ、プロジェクト）
4. クロスエンコーダーLLMスコアリングでリランク
5. 参照とメタデータ付きのトップ結果を返す

### 4. 統合
夜間の自動統合：
- ワーキングメモリを短期に移行
- 類似したメモリをクラスタリング
- 古い/重要でないメモリを忘却
- メモリ階層を維持

## パフォーマンス

Context Orchestratorは個人使用向けに最適化されています：

| 指標 | 目標 | 典型値 |
|------|------|--------|
| 検索レイテンシ | ≤200ms | ~80ms |
| 取り込み時間 | ≤5秒/会話 | ~2-3秒 |
| メモリフットプリント | ≤3GBピーク | ~1GB常駐 |
| ディスク使用量 | ~10MB/年 | 圧縮済み |
| 統合時間 | <5分/1万メモリ | ~2-3分 |

ベンチマークを実行：
```bash
python scripts/performance_profiler.py
```

## テスト

Context Orchestratorには包括的なテストカバレッジが含まれています：

```bash
# すべてのテストを実行
pytest

# ユニットテスト（48個のエッジケース）
pytest tests/unit/

# エンドツーエンドテスト
pytest tests/e2e/

# リグレッションテスト
python -m scripts.run_regression_ci

# 負荷テスト
python -m scripts.load_test --num-queries 100
python -m scripts.concurrent_test --concurrency 5
```

**テストカバレッジ**：
- ✅ 48個のエッジケーステスト（特殊文字、絵文字、極端な入力）
- ✅ 負荷テスト（メモリリーク検出）
- ✅ 並行テスト（スレッドセーフティ検証）
- ✅ 品質指標（Precision/Recall/F1）
- ✅ クエリパターンカバレッジ（50種類の多様なクエリ）

## アーキテクチャ

```
┌─────────────────────────────────────────┐
│   MCPクライアント (CLI/Cursor/VS Code)   │
└──────────────┬──────────────────────────┘
               │ stdio (JSON-RPC)
               ↓
┌─────────────────────────────────────────┐
│   Context Orchestrator (MCPサーバー)     │
│  ┌─────────────────────────────────┐   │
│  │ サービス: 取り込み、検索、        │   │
│  │ 統合、セッション管理              │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ モデルルーター (ローカル ↔ クラウド)│   │
│  └─────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   ストレージレイヤー                      │
│  • Chroma DB (ベクトル検索)              │
│  • BM25 Index (キーワード検索)           │
│  • セッションログ                        │
└─────────────────────────────────────────┘
```

詳細なアーキテクチャと開発ガイドについては、[CLAUDE.md](CLAUDE.md)を参照してください。

## ユースケース

### 1. バグトラブルシューティング
「先月修正した認証エラーを思い出して」
→ インシデント、根本原因、修正を即座に取得

### 2. コード再利用
「Pythonのリトライロジックの例を見せて」
→ コンテキスト付きで以前使用したコードスニペットを発見

### 3. 決定レビュー
「なぜMongoDBよりPostgreSQLを選んだのか？」
→ トレードオフ付きのアーキテクチャ決定を想起

### 4. 学習強化
「Pythonのasync/awaitについて何を学んだか？」
→ 思考プロセスと実験を表示

### 5. プロジェクトオンボーディング
「payment-serviceプロジェクトの主な課題は何か？」
→ 関連メモリのプロジェクトスコープ検索

## 設定

### モデルルーティング戦略

Context Orchestratorは複雑さに基づいてタスクをインテリジェントにルーティングします：

| タスク | モデル | 理由 |
|--------|--------|------|
| 埋め込み | ローカル（nomic-embed-text） | 常に必要、プライバシー重要 |
| 分類 | ローカル（Qwen2.5） | シンプル、プライバシー重要 |
| 短い要約 | ローカル（Qwen2.5） | 十分な品質 |
| 長い要約 | CLI（Claude/GPT） | 高品質が必要 |
| 複雑な推論 | CLI（Claude/GPT） | 高度な機能 |

`config.yaml`で設定できます：

```yaml
cli:
  command: claude  # または "codex"、空欄で100%ローカル処理

# 100%ローカル処理の場合は空に設定：
cli:
  command: ""
```

### Obsidian統合

Obsidianをメモ取りに使用している場合：

```yaml
obsidian_vault_path: C:\Users\username\Documents\ObsidianVault
```

Context Orchestratorは以下を実行します：
- 会話パターンの`.md`ファイルを監視
- `**User:**` / `**Assistant:**`の会話を抽出
- Wikilinks（`[[filename]]`）を解析して関係を追跡
- YAMLフロントマター（タグ、メタデータ）を解析

### 検索チューニング

検索動作を調整：

```yaml
search:
  vector_candidate_count: 100      # ベクトル検索候補数
  bm25_candidate_count: 30         # BM25検索候補数
  result_count: 10                 # 返される最終結果数
  cross_encoder_enabled: true      # LLMリランキングを有効化
  cross_encoder_top_k: 3           # LLMでリランクする数
  cross_encoder_cache_size: 128    # LLMスコアのキャッシュサイズ
  cross_encoder_cache_ttl_seconds: 900  # キャッシュTTL
```

### メモリ管理

忘却と統合を設定：

```yaml
forgetting:
  age_threshold_days: 30           # 30日後に忘却
  importance_threshold: 0.3        # 重要度 > 0.3 なら保持
  compression_enabled: true        # 忘却前に圧縮

clustering:
  similarity_threshold: 0.9        # 類似度 ≥ 0.9 でクラスタリング
  min_cluster_size: 2              # 最小クラスタサイズ

consolidation:
  schedule: "0 3 * * *"            # Cronスケジュール（毎日午前3時）
  auto_enabled: true               # 自動統合を有効化
```

## トラブルシューティング

### セットアップウィザードが失敗する

**問題**: セットアップウィザードがOllamaに接続できない

```bash
# Ollamaが実行中か確認
curl http://localhost:11434/api/tags
# Windowsの場合:
Invoke-WebRequest http://localhost:11434/api/tags

# 応答がない場合、別のターミナルでOllamaを起動
ollama serve

# モデルがインストールされているか確認
ollama list
```

**問題**: ポート11434が既に使用中

セットアップ実行前に `config.yaml.template` を編集：
```yaml
ollama:
  url: http://localhost:11435  # 別のポートを使用
```

### Pythonバージョンの問題

**問題**: "Python 3.11+ required" エラー

```bash
# Pythonバージョンを確認
python --version

# Python 3.11または3.12が必要（3.13以降は未テスト）
# Python 3.11のインストール:
# - Windows: https://www.python.org/downloads/
# - Ubuntu: sudo apt install python3.11
# - Mac: brew install python@3.11
```

### PowerShell実行ポリシーエラー（Windows）

**問題**: "スクリプトの実行が無効になっているため読み込めません"

```powershell
# 解決策1: 実行ポリシーを変更（推奨）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 解決策2: 一時的にバイパス
powershell -ExecutionPolicy Bypass -File .venv\Scripts\Activate.ps1
```

### Ollama接続の問題

```bash
# Ollamaが実行中か確認
curl http://localhost:11434/api/tags

# Ollamaを起動
ollama serve

# モデルがインストールされているか確認
ollama list

# モデルを直接テスト
ollama run nomic-embed-text "test"
```

### 検索結果が返されない

```bash
# メモリがインデックスされているか確認
python -m src.cli list-recent

# データベースが存在するか確認
ls ~/.context-orchestrator/chroma_db/
# Windows: dir %USERPROFILE%\.context-orchestrator\chroma_db

# 診断を実行
python -m src.cli doctor

# ログを確認
tail -f ~/.context-orchestrator/logs/context_orchestrator.log
# Windows: Get-Content -Wait ~/.context-orchestrator/logs/context_orchestrator.log -Tail 50
```

### 高メモリ使用量

```bash
# 統合ステータスを確認
python -m src.cli status

# 手動統合を実行
python -m src.cli consolidate

# 古いメモリをエクスポートして削除
python -m src.cli export --output backup_$(date +%Y%m%d).json
```

### PowerShellラッパーが動作しない（Windows）

```powershell
# ラッパーがロードされているか確認
Get-Command claude

# プロファイルをリロード
. $PROFILE

# セットアップを再実行
python scripts/setup.py --repair
```

### インポートエラーまたは依存関係の欠落

```bash
# 依存関係を再インストール
pip install -r requirements.txt --upgrade

# 特定のパッケージが失敗する場合、個別にインストール
pip install chromadb tiktoken rank-bm25 pyyaml requests watchdog apscheduler

# インストール済みパッケージを確認
pip list
```

## プライバシーとセキュリティ

### データ保護
- **すべてのデータをローカルに保存** `~/.context-orchestrator/`
- **OS レベルのアクセス制御**（ファイルパーミッション）
- **テレメトリや外部トラッキングなし**
- **エクスポート/インポート**で手動バックアップ

### プライバシーに敏感な処理
- **埋め込み**: 常にローカル（nomic-embed-text）
- **分類**: 常にローカル（Qwen2.5）
- **検索**: 常にローカル（クラウドAPIコールなし）
- **要約**: 短いものはローカル、長いものはクラウド（設定可能）

### クラウドLLM使用（オプション）
- **最小限のコンテキスト**: 必要なコンテンツのみ送信
- **ユーザー同意**: セットアップウィザードで設定を確認
- **フォールバック**: クラウド利用不可時はローカルLLMに切り替え
- **記録なし**: 内部呼び出しはメモリキャプチャをスキップ

## ロードマップ

### v0.1.0（現在のリリース）
✅ コアメモリキャプチャと検索
✅ ハイブリッド検索（ベクトル + BM25）
✅ クロスエンコーダーリランキング
✅ クエリ属性抽出
✅ プロジェクト管理
✅ 検索ブックマーク
✅ 包括的なテストスイート

### v0.2.0（予定）
🔄 プロジェクト初期化（`/init`コマンド）
🔄 コードベーススキャンとインデックス化
🔄 ファイルレベルのメモリ関連付け
🔄 強化されたObsidian統合

### 将来の検討事項
💡 メモリ探索用のWeb UI
💡 チームコラボレーション機能
💡 カスタムスキーマ定義
💡 拡張性のためのプラグインシステム

## 貢献

貢献を歓迎します！詳細は[CONTRIBUTING.md](CONTRIBUTING.md)を参照してください：
- 開発環境のセットアップ
- コードスタイル要件
- テスト要件
- プルリクエストプロセス

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細は[LICENSE](LICENSE)を参照してください。

## 謝辞

- **Ollama** - ローカルLLMランタイム
- **Chroma** - ベクトルデータベース
- **Model Context Protocol（MCP）** - 標準化された統合
- **すべての貢献者** - このプロジェクトを可能にしてくれた方々

## サポート

- **Issues**: [GitHub Issues](https://github.com/myo-ojin/llm-brain/issues)
- **ドキュメント**: [CLAUDE.md](CLAUDE.md)（開発者ガイド）
- **ディスカッション**: [GitHub Discussions](https://github.com/myo-ojin/llm-brain/discussions)

## 引用

研究やプロジェクトでContext Orchestratorを使用する場合は、引用してください：

```bibtex
@software{context_orchestrator,
  title = {Context Orchestrator: 開発者のための外部脳システム},
  author = {Context Orchestrator Contributors},
  year = {2025},
  url = {https://github.com/myo-ojin/llm-brain}
}
```

---

**プライバシーと知識の継続性を重視する開発者のために ❤️ で構築**
