# テスト実行ガイド

## 概要

Context Orchestratorには3種類のテストがあります：

1. **ユニットテスト** (`tests/unit/`) - 個別コンポーネントのテスト
2. **E2Eテスト** (`tests/e2e/`) - エンドツーエンドワークフローのテスト
3. **統合テスト** - 実環境での統合テスト（ドキュメントのみ）

## 前提条件

### 最小要件（モックテスト用）
```bash
pip install -r requirements.txt
```

### 完全要件（実環境テスト用）
```bash
# 依存関係
pip install -r requirements.txt

# Ollamaサービス
ollama serve

# 必要なモデル
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
```

## テスト実行方法

### 1. すべてのテスト実行
```bash
pytest
```

### 2. ユニットテストのみ
```bash
pytest tests/unit/ -v
```

### 3. E2Eテストのみ
```bash
pytest tests/e2e/ -v
```

### 4. カバレッジレポート
```bash
pytest --cov=src --cov-report=html
# レポート: htmlcov/index.html
```

### 5. 特定のテストファイル
```bash
pytest tests/e2e/test_full_workflow.py -v
```

### 6. 特定のテストケース
```bash
pytest tests/e2e/test_full_workflow.py::TestEndToEndWorkflow::test_basic_ingestion_and_retrieval -v
```

## テストの種類

### ユニットテスト（モック使用）
Ollama不要。モックで依存関係を置き換え。

- `test_chunker.py` - テキストチャンク化
- `test_ingestion.py` - 会話取り込み
- `test_search.py` - メモリ検索
- `test_consolidation.py` - メモリ統合
- `test_obsidian_parser.py` - Obsidianファイル解析
- `test_protocol_handler.py` - MCPプロトコル

### E2Eテスト（モック使用）
Ollama不要。モックLLMクライアントで実行。

**TestEndToEndWorkflow**:
- 基本的な取り込みと取得
- 複数会話の取得とランキング
- 統合ワークフロー
- 特殊文字検索
- 長文コンテンツ
- 日本語テキスト
- コードブロック保存
- 検索結果ランキング

**TestErrorHandling**:
- 必須フィールド欠落
- 空コンテンツ
- 空クエリ

**TestPerformance**:
- 検索レイテンシ
- バッチ取り込みスループット

## 制限事項

### GitHub/CI環境
- ✅ ユニットテスト（モック）: 実行可能
- ✅ E2Eテスト（モック）: 実行可能
- ❌ 統合テスト: Ollama必須
- ❌ パフォーマンステスト: 実環境必須

### ローカル環境
- ✅ すべてのテスト実行可能
- ✅ パフォーマンスプロファイリング可能

## トラブルシューティング

### ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### Ollama接続エラー
```bash
# Ollamaサービス起動
ollama serve

# 別のターミナルでテスト実行
pytest tests/integration/
```

### モデル未インストール
```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
```

## パフォーマンステスト

実環境でのパフォーマンス測定：
```bash
# 基本実行
python scripts/performance_profiler.py

# カスタム実行回数
python scripts/performance_profiler.py --runs 200

# レポート保存
python scripts/performance_profiler.py --output ./perf_report.json
```

## 参考資料

- [INTEGRATION_TEST_RESULTS.md](../INTEGRATION_TEST_RESULTS.md) - 統合テスト結果
- [TESTING_ON_GITHUB.md](../TESTING_ON_GITHUB.md) - GitHub環境でのテスト制限
- [CLAUDE.md](../CLAUDE.md) - 開発ガイド
