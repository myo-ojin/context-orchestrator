# Issue Log - Context Orchestrator

このファイルは実装・運用中に発生した課題を管理するためのログです。

## 運用ルール
- 新しい課題は **Open Issues** テーブルに追記し、ID を一意に割り当てる。
- 対応状況が変わったら Status / Next Action を更新し、解決したら **Resolved Issues** に移動する。
- 解決時には「原因」と「対処内容」を Issue Details の該当節に追記し、再発防止策があれば記録する。

## Open Issues

| ID | Title | Status | Created | Owner | Next Action |
|----|-------|--------|---------|-------|-------------|
| #2025-11-03-03 | Phase5 coreサービス未実装 | Monitoring | 2025-11-03 | TBD | 残TODO整理・Phase6連携 |

## Resolved Issues

| ID | Title | Resolved | Owner | Notes |
|----|-------|----------|-------|-------|
| #2025-11-05-07 | main.py と各クラスの __init__ 引数が多数不一致 | 2025-11-05 | TBD | main.py の ModelRouter, IngestionService, ConsolidationService の呼び出しを修正。全初期化エラーを解消し、MCP サーバーが正常起動。 |
| #2025-11-05-06 | LocalLLMClient が embedding_model / inference_model 引数を受け取らない | 2025-11-05 | TBD | __init__ に引数追加、generate_embedding / generate メソッドでデフォルト使用、health_check 呼び出し削除。 |
| #2025-11-05-05 | BM25Index の引数名が main.py と不一致 | 2025-11-05 | TBD | main.py が index_path を渡すが、BM25Index は persist_path を期待。main.py を修正。 |
| #2025-11-05-04 | ChromaVectorDB が collection_name 引数を受け取らない | 2025-11-05 | TBD | __init__ に collection_name 引数を追加。main.py と cli.py から正しく呼び出せるよう修正。 |
| #2025-11-05-03 | モデル名 nomic-embed-text-v1.5 が存在しない | 2025-11-05 | TBD | 全22ファイルで nomic-embed-text に統一。Ollama レジストリに存在する正しいモデル名に修正。 |
| #2025-11-05-02 | SearchService に get_memory / list_recent メソッドがない | 2025-11-05 | TBD | MCPProtocolHandler と CLI が呼び出す2つのメソッドを実装。全154テスト合格確認。 |
| #2025-11-03-01 | Ollama 埋め込み API 呼び出しが 400 エラーになる | 2025-11-03 | TBD | `generate_embedding` を `input` キーで呼ぶよう修正。今後はユニットテスト追加を検討。 |
| #2025-11-03-02 | Chunk メタデータに memory_id が入らず後工程で利用できない | 2025-11-03 | TBD | Chunker/Indexer で `memory_id` / `chunk_index` をメタデータへ埋め込み、検索・削除で参照可能にした。 |
| #2025-11-09-01 | Hybrid search/rerank modernization plan | Proposed | 2025-11-09 | ryomy | QAM導入＋cross-encoder再ランク＋tier別recency設計 |

## Issue Details

### #2025-11-05-07 main.py と各クラスの __init__ 引数が多数不一致
- **現象**: Phase 8-9 で実装した `main.py` が、Phase 1-7 で実装した各クラスを初期化する際、引数名の不一致や必須引数の不足により、複数のクラスで初期化エラーが連鎖的に発生する。MCP サーバーが起動できない。
- **影響**: Context Orchestrator が全く起動できず、システムが使用不可。エラーが連鎖的に発生するため、1つ修正しても次のエラーが出る状態。
- **原因**: Phase 8-9 で `main.py` の初期化ロジックを実装した際、Phase 1-7 で実装済みの各クラスの `__init__` シグネチャを正確に確認せず、推測で引数を渡したため。統合テストが不足していた。
- **発見した不一致 (2025-11-05)**:
  1. **ModelRouter** (main.py:124-127):
     - 呼び出し: `local_llm=..., cli_llm=...`
     - 期待値: `local_llm_client=..., cli_llm_client=...`
     - 修正方法: main.py の引数名を変更
  2. **IngestionService** (main.py:195-200):
     - 呼び出し: `schema_classifier=..., chunker=..., indexer=..., model_router=...`
     - 期待値: `vector_db=..., classifier=..., chunker=..., indexer=..., model_router=...`
     - 問題: (a) `schema_classifier` → `classifier`, (b) `vector_db` 引数が不足
     - 修正方法: main.py で引数名変更 + `vector_db` 追加
  3. **ConsolidationService** (main.py:216-224):
     - 呼び出し: `vector_db, model_router, similarity_threshold, min_cluster_size, age_threshold_days, importance_threshold, retention_hours`
     - 期待値: `vector_db, indexer, model_router, similarity_threshold, age_threshold_days, importance_threshold, working_memory_retention_hours`
     - 問題: (a) `indexer` 引数が不足, (b) `min_cluster_size` が余分, (c) `retention_hours` → `working_memory_retention_hours`
     - 修正方法: main.py で引数追加・削除・名前変更
- **既に修正済みの問題**:
  - ChromaVectorDB: `collection_name` 引数追加 (#2025-11-05-04)
  - BM25Index: `index_path` → `persist_path` (#2025-11-05-05)
  - LocalLLMClient: `embedding_model`, `inference_model` 引数追加 (#2025-11-05-06)
- **修正方針**: 各クラスの実装は Phase 1-7 で完成しており、テストも通過している。実装側を変更するとテストコードへの影響が大きいため、**main.py の呼び出し側を修正する**方針を採用。段階的に1つずつ修正してテストを繰り返す。
- **対処計画 (2025-11-05)**:
  1. ModelRouter の引数名修正 → テスト
  2. IngestionService の引数修正 → テスト
  3. ConsolidationService の引数修正 → テスト
  4. 全修正完了後、MCP サーバー起動確認
- **対処内容 (2025-11-05 実施完了)**:
  1. **修正1 - ModelRouter** (main.py:124-127):
     - `local_llm=local_llm` → `local_llm_client=local_llm`
     - `cli_llm=cli_llm` → `cli_llm_client=cli_llm`
     - テスト結果: ✅ ModelRouter 初期化成功、次のエラー（IngestionService）に進行
  2. **修正2 - IngestionService** (main.py:195-200):
     - `vector_db=vector_db` を第1引数として追加
     - `schema_classifier=classifier` → `classifier=classifier`
     - テスト結果: ✅ IngestionService 初期化成功、次のエラー（ConsolidationService）に進行
  3. **修正3 - ConsolidationService** (main.py:217-224):
     - `indexer=indexer` を第2引数として追加
     - `min_cluster_size=config.clustering.min_cluster_size` の行を削除
     - `retention_hours=config.working_memory.retention_hours` → `working_memory_retention_hours=config.working_memory.retention_hours`
     - テスト結果: ✅ ConsolidationService 初期化成功
- **検証結果 (2025-11-05)**:
  - ✅ 全12コンポーネント（Storage, Models, Processing, Services, MCP Handler）が正常に初期化
  - ✅ MCP サーバーが正常起動し、"Ready to accept requests on stdin" を表示
  - ✅ エラーなく動作確認完了
- **再発防止**:
  - Phase 完了時に実際の起動テストを必ず実施する
  - main.py 実装時は各クラスの __init__ シグネチャを必ず確認する
  - 統合テスト (main() の起動テスト) を追加する
  - 型チェック (mypy) の導入を検討する

### #2025-11-05-05 BM25Index の引数名が main.py と不一致
- **現象**: `python -m src.main` 実行時に `BM25Index.__init__() got an unexpected keyword argument 'index_path'` エラーが発生し、ストレージ初期化に失敗する。
- **影響**: MCP サーバーが起動できず、システムが使用不可。ChromaVectorDB の初期化は成功するが、BM25Index で失敗する。
- **原因**: `main.py` (82行目) が `BM25Index(index_path=str(bm25_path))` と呼び出しているが、`src/storage/bm25_index.py` (38行目) の `__init__` は `persist_path` を引数名として定義している。引数名の不一致。
- **対処内容 (2025-11-05)**:
  - `main.py` 82行目を修正:
    - 修正前: `BM25Index(index_path=str(bm25_path))`
    - 修正後: `BM25Index(persist_path=str(bm25_path))`
  - cli.py は BM25Index を使用していないため修正不要
- **検証**: `python -m src.main` で起動確認が必要
- **再発防止**: ChromaVectorDB と同様、インターフェース設計時に呼び出し側と実装側の引数名を統一する。型チェック（mypy）の活用も検討。

### #2025-11-05-04 ChromaVectorDB が collection_name 引数を受け取らない
- **現象**: `python -m src.main` 実行時に `ChromaVectorDB.__init__() got an unexpected keyword argument 'collection_name'` エラーが発生し、起動に失敗する。
- **影響**: Context Orchestrator の MCP サーバーが起動できず、システムが全く使えない状態。CLI コマンドも同様にエラーで失敗する。
- **原因**: `main.py` (73-76行目) と `cli.py` (3箇所) が `ChromaVectorDB(collection_name='context_orchestrator', persist_directory=...)` という形式で呼び出しているが、`src/storage/vector_db.py` の `__init__` メソッドが `collection_name` 引数を受け取っていなかった。コレクション名が `"memories"` としてハードコードされていた。
- **対処内容 (2025-11-05)**:
  - `ChromaVectorDB.__init__` のシグネチャを変更:
    - 修正前: `def __init__(self, persist_directory: str):`
    - 修正後: `def __init__(self, persist_directory: str, collection_name: str = "memories"):`
  - ハードコードされていた `name="memories"` を `name=collection_name` に変更
  - デフォルト値 `"memories"` を設定し、後方互換性を保持
  - ログ出力も動的なコレクション名を表示するよう修正
- **検証**: `python -m src.main` で起動確認が必要
- **再発防止**:
  - インターフェース設計時に、呼び出し側と実装側の引数を統一する
  - Phase 完了時に実際の起動テストを実施する
  - 統合テストで main() の起動確認を追加することを検討

### #2025-11-05-03 モデル名 nomic-embed-text-v1.5 が存在しない
- **現象**: プロジェクト全体で埋め込みモデル名として `nomic-embed-text-v1.5` が指定されていたが、Ollama レジストリにこのモデル名は存在せず、`ollama pull nomic-embed-text-v1.5` が "file does not exist" エラーで失敗する。
- **影響**: セットアップウィザード (`scripts/setup.py`) がモデルのダウンロードに失敗し、システムのセットアップが完了できない。ユーザーは手動で設定ファイルを修正する必要があり、初回セットアップの体験が非常に悪い。
- **原因**: プロジェクト設計時に `nomic-embed-text-v1.5` というモデル名を想定していたが、実際の Ollama レジストリでは `nomic-embed-text` (または `nomic-embed-text:latest`) が正しいモデル名。バージョンタグ `-v1.5` は Ollama の命名規則に存在しない。
- **対処内容 (2025-11-05)**:
  - プロジェクト全体で `nomic-embed-text-v1.5` を検索し、22ファイルで発見
  - 全てのファイルで `nomic-embed-text` に一括置換:
    - 設定ファイル: `config.yaml.template`, `src/config.py`, `scripts/doctor.py`
    - ドキュメント: `CLAUDE.md`, `README.md`, `SETUP_GUIDE.md`
    - 仕様書: `.kiro/specs/dev-knowledge-orchestrator/*.md` (4ファイル)
    - ソースコード: `src/services/search.py`, `src/models/__init__.py`, `src/models/local_llm.py`, `src/models/router.py`, `src/storage/vector_db.py`, `src/utils/errors.py`
    - テスト: `test_basic.py`, `tests/test_phase3_models.py`
    - その他: `designtt.txt`
    - バックアップ: `.bak` ファイル (3ファイル)
  - 置換後、`grep` で確認し、プロジェクト内に `nomic-embed-text-v1.5` が残っていないことを検証
  - 修正後のモデル名 `nomic-embed-text` は Ollama で正常にダウンロード可能
- **再発防止**:
  - 新しい依存関係やモデルを追加する際は、公式ドキュメントで名前を確認する
  - セットアップスクリプトに実際のモデル存在確認を追加することを検討
  - プロジェクトテンプレート作成時に、実環境での動作確認を行う

### #2025-11-05-02 SearchService に get_memory / list_recent メソッドがない
- **現象**: MCPProtocolHandler が `search_service.get_memory(memory_id)` と `search_service.list_recent(limit, filter_metadata)` を呼び出すが、SearchService にこれらのメソッドが実装されていなかった。
- **影響**: MCP ツール `get_memory` と `list_recent_memories` が実行時エラーとなり、クライアントから個別メモリの取得や最近のメモリ一覧の取得ができない。CLI の `list-recent` コマンドも動作しない。
- **原因**: Phase 7 で MCP handler を実装した際、SearchService に必要なメソッドを追加し忘れた。Phase 5 で SearchService の基本的な検索機能は実装したが、個別取得と一覧取得のメソッドが不足していた。
- **対処内容 (2025-11-05)**:
  - SearchService に以下の2つのメソッドを実装:
    1. `get_memory(memory_id: str) -> Optional[Dict[str, Any]]`: 指定された memory_id のメモリエントリと関連チャンクを取得
    2. `list_recent(limit: int = 20, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]`: 最近のメモリを timestamp 降順で取得
  - VectorDB の `get()` と `list_by_metadata()` を使用して実装
  - 適切なエラーハンドリングとロギングを追加
  - 全 154 ユニットテストが合格することを確認
  - 詳細は `.kiro/specs/dev-knowledge-orchestrator/PHASE9_FIXES.md` に記録
- **再発防止**: サービス層のメソッドを追加する際は、呼び出し側（MCP handler / CLI）との整合性を事前にチェックする。Phase 完了時に統合テストを実施する。

### #2025-11-03-03 Phase5 coreサービス未実装
- **現象**: Phase5 で想定していた Consolidation / 削除フローが未実装のまま残っており、Session/Fuse 連携が動作しない。
- **影響**: ConsolidationService・Indexer の欠落により、メモリ削除やクラスタリングが実行時に失敗する。
- **進捗 (2025-11-03)**: ConsolidationService の migrate / cluster / forget 実装、Indexer.delete_by_memory_id、SearchService のフィルタ処理を実装。`pytest` 69 passed / 10 skipped、`pytest --cov=src` でカバレッジ 61% を確認。
- **残課題**: Consolidation stats のメタデータ集計、LLM クライアント層のモック整備、Phase6 以降の機能追加時に再検証する。
### #2025-11-09-01 Hybrid search/rerank modernization plan
- **背景 / 課題**: timeline や change-feed など意図が明確なクエリでも working/short の最新メモが常に上位を占拠し、本来参照したい長期メモや専用トピックが埋もれている。bm25 が強い chunk がサマリより上に出るケースも残っており、現行ルールベース `_rerank` では改善の頭打ち。citereports/mcp_runs/mcp_run-20251109-035415.jsonl
- **外部ベストプラクティス**:
  1. Query Attribute Modeling (QAM) でクエリ属性を抽出し、ハイブリッド検索へ渡すと mAP が向上。citehttps://arxiv.org/abs/2508.04683?utm_source=openai
  2. HYRR のようにハイブリッド retriever を前提に学習した cross-encoder rerank を入れるとランキング精度が安定。citehttps://arxiv.org/abs/2212.10528?utm_source=openai
  3. CLEF CheckThat! 2025 優勝構成では dense 多め + BM25 少なめの候補を cross-encoder に渡して Precision@5 を大幅改善。citehttps://arxiv.org/abs/2505.23250?utm_source=openai
  4. CaGR-RAG のようにクエリをクラスタリングして実行順を最適化すると tail latency を 51% 削減。citehttps://arxiv.org/abs/2505.01164?utm_source=openai
- **Next Actions**:
  1. LLM でクエリ属性 (topic/type/project) を抽出し、SearchService のフィルタ/metadata bonus に適用。
  2. dense100 + BM2530 の候補を cross-encoder (BGE 等) に渡す rerank パスを追加し、ルール型 `_rerank` は fallback にする。
  3. tier ごとに recency 係数を持てるよう `_calculate_recency_score` を再設計し、長期メモも vector/BM25 で浮上可能にする。
  4. chunk はランキング対象から除外し、選ばれたメモの補足情報としてのみ返す。
  5. `scripts.mcp_replay` で Precision@k / NDCG@k を自動計測し、クエリをトピックごとにバッチ処理して I/O キャッシュ効率を向上。
