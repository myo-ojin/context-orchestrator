# Context Orchestrator セットアップガイド

## ステップ0: 前提条件

### Python 環境の準備

**Python 3.11 以上**が必要です。確認：
```powershell
python --version
```

### 依存パッケージのインストール（重要！）

プロジェクトディレクトリで以下を実行：

```powershell
pip install -r requirements.txt
```

**インストールされるパッケージ:**
- chromadb - ベクトルデータベース（約200MB）
- tiktoken - トークンカウント
- rank-bm25 - キーワード検索
- pyyaml - 設定ファイル読み込み
- requests - HTTP通信
- その他の依存関係

**インストール時間:** 5-10分程度（chromadb が大きいため）

---

## ステップ1: インポートテスト ✓ 完了

全てのPythonモジュールが正常にインポートできました！

## ステップ2: Ollama のインストール

### Windows の場合

1. **Ollama をダウンロード**
   - 公式サイト: https://ollama.ai/
   - Windows版をダウンロード: https://ollama.ai/download/windows
   - インストーラーを実行

2. **インストール確認**
   ```powershell
   ollama --version
   ```

   出力例: `ollama version is 0.x.x`

3. **Ollama サーバーを起動**
   ```powershell
   ollama serve
   ```

   別のターミナルを開いて以下を実行（サーバーは起動したまま）：
   ```powershell
   curl http://localhost:11434/api/tags
   ```

   JSONレスポンスが返ってくればOK

### macOS / Linux の場合

```bash
# インストール
curl -fsSL https://ollama.ai/install.sh | sh

# バージョン確認
ollama --version

# サーバー起動
ollama serve
```

---

## ステップ3: 必要なモデルのダウンロード

**重要**: 以下のモデルが必要です（合計約4GB）

### 3.1 埋め込みモデル（必須）
```bash
ollama pull nomic-embed-text
```
- サイズ: ~274MB
- 用途: テキストをベクトル化して検索

### 3.2 推論モデル（必須）
```bash
ollama pull qwen2.5:7b
```
- サイズ: ~4.7GB
- 用途: スキーマ分類、要約生成

### ダウンロード確認
```bash
ollama list
```

出力例:
```
NAME                      ID              SIZE      MODIFIED
nomic-embed-text     ...             274 MB    ...
qwen2.5:7b                ...             4.7 GB    ...
```

---

## ステップ4: セットアップウィザードの実行

**自動セットアップ（推奨）:**
```bash
python scripts/setup.py
```

セットアップウィザードが以下を実行します：
1. Ollama の接続確認
2. 必要なモデルの自動ダウンロード
3. データディレクトリの作成
4. Obsidian Vault パスの設定（オプション）
5. CLI LLM の選択（claude/codex）
6. 設定ファイルの生成

**手動セットアップ:**
```bash
# 1. 設定ファイルを作成
cp config.yaml.template ~/.context-orchestrator/config.yaml

# 2. 設定ファイルを編集
notepad ~/.context-orchestrator/config.yaml  # Windows
nano ~/.context-orchestrator/config.yaml     # Linux/Mac
```

---

## ステップ5: ヘルスチェック

```bash
python scripts/doctor.py
```

チェック項目:
- [x] Ollama Running - Ollamaが起動しているか
- [x] Ollama Models - 必要なモデルがインストールされているか
- [x] Data Directory - データディレクトリが存在するか
- [x] Chroma DB - ベクトルDBにアクセス可能か
- [x] Config File - 設定ファイルが存在するか

**全てPASSすればOK！**

---

## ステップ6: Context Orchestrator の起動

### 6.1 MCPサーバーとして起動
```bash
python -m src.main
```

ログ出力例:
```
============================================================
Context Orchestrator Starting
============================================================
Initialized Chroma DB: C:\Users\...\chroma_db
Initialized BM25 Index: C:\Users\...\bm25_index.pkl
Connected to Ollama: http://localhost:11434
Initialized Model Router
Initialized processing components
Initialized IngestionService
Initialized SearchService
Initialized ConsolidationService
MCP Protocol Handler initialized
Ready to accept requests on stdin
============================================================
```

### 6.2 CLIコマンドでテスト
```bash
# システムステータス確認
python -m src.cli status

# ヘルスチェック
python -m src.cli doctor

# 最近の記憶を一覧表示（まだ空）
python -m src.cli list-recent
```

---

## ステップ7: PowerShell ラッパーのインストール（オプション）

Claude CLI や Codex CLI を自動記録したい場合：

```powershell
# インストール
powershell -ExecutionPolicy Bypass -File scripts/setup_cli_recording.ps1 -Install

# PowerShell を再起動

# テスト
claude "hello"  # この会話が自動的に記録される
```

アンインストール:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_cli_recording.ps1 -Uninstall
```

---

## トラブルシューティング

### Ollama が起動しない
```bash
# Windows: サービスを確認
Get-Service Ollama

# 手動起動
ollama serve
```

### モデルのダウンロードが遅い
- 4-5GB のダウンロードなので10-30分かかる場合があります
- ネットワーク接続を確認してください

### Chroma DB エラー
```bash
# データベースを削除して再作成
rm -rf ~/.context-orchestrator/chroma_db
```

### 設定ファイルが見つからない
```bash
# テンプレートから作成
python -c "from src.config import Config, save_config; save_config(Config())"
```

---

## 次のステップ

1. **動作確認完了後:**
   - Phase 10: 深夜統合スケジューラー（オプション）
   - Phase 11: Obsidian統合（オプション）

2. **実際に使ってみる:**
   - Claude CLI で会話 → 自動記録
   - `python -m src.cli search "キーワード"` で検索

3. **MCP クライアントと接続:**
   - Cursor, VS Code, Kiro などのMCPクライアントから接続可能
