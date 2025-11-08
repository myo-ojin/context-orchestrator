# Phase 15: プロジェクト管理と検索改善 - 詳細タスクリスト

## 概要
NotebookLM Skillの分析結果を基に、プロジェクト別の記憶管理と検索改善機能を追加する。
既存のローカル優先・プライバシー重視の設計思想を維持しつつ、UXを向上させる。

参照: `NOTEBOOKLM_COMPARISON_ANALYSIS.md`

---

## Phase 15: Project Management & Search Enhancement

### 15. プロジェクト管理と検索改善

#### 15.1 データモデルの拡張
- [ ] 15.1.1 `Project` dataclassを定義（`src/models/__init__.py`）
  - **実装内容**:
    ```python
    @dataclass
    class Project:
        id: str                    # UUID
        name: str                  # プロジェクト名
        description: str           # 説明
        tags: List[str]            # タグ（例: ["react", "typescript"]）
        created_at: datetime       # 作成日時
        updated_at: datetime       # 更新日時
        memory_count: int = 0      # 紐付けられた記憶数
        last_accessed: datetime    # 最終アクセス日時
        metadata: Dict[str, Any]   # 追加メタデータ
    ```
  - **ファイル**: `src/models/__init__.py`
  - **参照**: 既存の`Memory` dataclassと同様の構造
  - _Requirements: 新規（Phase 15 - Project Management）_

- [ ] 15.1.2 `SearchBookmark` dataclassを定義（`src/models/__init__.py`）
  - **実装内容**:
    ```python
    @dataclass
    class SearchBookmark:
        id: str                    # UUID
        name: str                  # ブックマーク名
        query: str                 # 検索クエリ
        filters: Dict[str, Any]    # フィルター条件
        created_at: datetime       # 作成日時
        usage_count: int = 0       # 使用回数
        last_used: datetime        # 最終使用日時
    ```
  - **ファイル**: `src/models/__init__.py`
  - _Requirements: 新規（Phase 15 - Search Bookmarks）_

- [ ] 15.1.3 `Memory` dataclassに`project_id`フィールドを追加
  - **実装内容**: `project_id: Optional[str] = None`を追加
  - **ファイル**: `src/models/__init__.py`
  - **影響範囲**: 既存コードとの互換性を保つため`Optional`
  - _Requirements: 新規（Phase 15 - Project Association）_

#### 15.2 ストレージ層の実装

- [ ] 15.2.1 `ProjectStorage`クラスを実装（`src/storage/project_storage.py`）
  - **実装内容**:
    - `save_project(project: Project) -> None`: JSONファイルに保存
    - `load_project(project_id: str) -> Optional[Project]`: プロジェクト読み込み
    - `list_projects() -> List[Project]`: 全プロジェクト一覧
    - `delete_project(project_id: str) -> bool`: プロジェクト削除
    - `update_project(project: Project) -> None`: プロジェクト更新
  - **ファイル**: 新規作成 `src/storage/project_storage.py`
  - **データファイル**: `~/.context-orchestrator/projects.json`
  - **参照**: `BM25Index`の永続化パターンを参考
  - _Requirements: 新規（Phase 15 - Project Storage）_

- [ ] 15.2.2 `BookmarkStorage`クラスを実装（`src/storage/bookmark_storage.py`）
  - **実装内容**:
    - `save_bookmark(bookmark: SearchBookmark) -> None`
    - `load_bookmark(bookmark_id: str) -> Optional[SearchBookmark]`
    - `list_bookmarks() -> List[SearchBookmark]`
    - `delete_bookmark(bookmark_id: str) -> bool`
    - `increment_usage(bookmark_id: str) -> None`
  - **ファイル**: 新規作成 `src/storage/bookmark_storage.py`
  - **データファイル**: `~/.context-orchestrator/bookmarks.json`
  - _Requirements: 新規（Phase 15 - Bookmark Storage）_

#### 15.3 ProjectManagerサービスの実装

- [ ] 15.3.1 `ProjectManager`クラスの基本構造を実装（`src/services/project_manager.py`）
  - **実装内容**:
    ```python
    class ProjectManager:
        def __init__(self, project_storage: ProjectStorage, vector_db: ChromaVectorDB):
            self.project_storage = project_storage
            self.vector_db = vector_db
    ```
  - **ファイル**: 新規作成 `src/services/project_manager.py`
  - **参照**: 既存の`IngestionService`のコンストラクタパターン
  - _Requirements: 新規（Phase 15 - Project Service）_

- [ ] 15.3.2 プロジェクト作成機能を実装
  - **メソッド**: `create_project(name: str, description: str, tags: List[str]) -> Project`
  - **処理**:
    1. UUIDを生成
    2. Projectオブジェクトを作成
    3. ProjectStorageに保存
    4. 作成されたProjectを返す
  - **ファイル**: `src/services/project_manager.py`
  - _Requirements: 新規（Phase 15 - Create Project）_

- [ ] 15.3.3 プロジェクト一覧取得機能を実装
  - **メソッド**: `list_projects(sort_by: str = 'updated_at') -> List[Project]`
  - **処理**:
    1. ProjectStorageから全プロジェクトを読み込み
    2. sort_byでソート（'updated_at', 'name', 'memory_count'等）
    3. ソート済みリストを返す
  - **ファイル**: `src/services/project_manager.py`
  - _Requirements: 新規（Phase 15 - List Projects）_

- [ ] 15.3.4 プロジェクト更新機能を実装
  - **メソッド**: `update_project(project_id: str, **updates) -> Project`
  - **処理**:
    1. プロジェクトを読み込み
    2. フィールドを更新
    3. updated_atを更新
    4. 保存して返す
  - **ファイル**: `src/services/project_manager.py`
  - _Requirements: 新規（Phase 15 - Update Project）_

- [ ] 15.3.5 プロジェクト削除機能を実装
  - **メソッド**: `delete_project(project_id: str, delete_memories: bool = False) -> bool`
  - **処理**:
    1. delete_memories=Trueの場合、紐付いた記憶も削除
    2. delete_memories=Falseの場合、記憶のproject_idをNoneに設定
    3. プロジェクトを削除
  - **ファイル**: `src/services/project_manager.py`
  - _Requirements: 新規（Phase 15 - Delete Project）_

- [ ] 15.3.6 プロジェクト自動選択機能を実装
  - **メソッド**: `auto_select_project(query: str, context: str = "") -> Optional[str]`
  - **処理**:
    1. クエリとコンテキストから関連プロジェクトを推測
    2. プロジェクト名・タグとの類似度を計算
    3. 最も関連性の高いproject_idを返す
  - **ファイル**: `src/services/project_manager.py`
  - **実装**: 簡易的なキーワードマッチング（将来的にLLM活用も可）
  - _Requirements: 新規（Phase 15 - Auto Select Project）_

#### 15.4 IngestionServiceの拡張

- [ ] 15.4.1 IngestionServiceにプロジェクト紐付け機能を追加
  - **変更内容**: `ingest_conversation`メソッドに`project_id`パラメータを追加
  - **シグネチャ**: `ingest_conversation(conversation: Dict, project_id: Optional[str] = None) -> str`
  - **処理**:
    1. project_idが指定されていればMemoryに設定
    2. 指定されていない場合は`auto_select_project`を呼び出して推測（オプション）
    3. プロジェクトのmemory_countをインクリメント
  - **ファイル**: `src/services/ingestion.py`
  - **注意**: 既存の呼び出し元との互換性を保つため、デフォルト値を使用
  - _Requirements: 既存Requirement 1の拡張_

#### 15.5 SearchServiceの拡張

- [ ] 15.5.1 SearchServiceにプロジェクトフィルター機能を追加
  - **メソッド**: `search_in_project(project_id: str, query: str, top_k: int = 10) -> List[Dict]`
  - **処理**:
    1. 通常の検索を実行
    2. project_idでフィルタリング
    3. フィルター済み結果を返す
  - **ファイル**: `src/services/search.py`
  - _Requirements: 既存Requirement 8の拡張_

- [ ] 15.5.2 SearchServiceに使用履歴記録機能を追加
  - **メソッド**: `_record_search_history(query: str, memory_ids: List[str]) -> None`
  - **処理**:
    1. 検索クエリとアクセスされた記憶IDを記録
    2. JSONファイルに追記
  - **ファイル**: `src/services/search.py`
  - **データファイル**: `~/.context-orchestrator/search_history.json`
  - _Requirements: 新規（Phase 15 - Search History）_

- [ ] 15.5.3 使用履歴を考慮したリランキング機能を追加
  - **メソッド**: `_rerank_with_history(results: List[Dict], query: str) -> List[Dict]`
  - **処理**:
    1. 過去の検索パターンを分析
    2. よくアクセスされる記憶にブーストを適用
    3. リランキングされた結果を返す
  - **ファイル**: `src/services/search.py`
  - **統合**: 既存の`_rerank`メソッドから呼び出し
  - _Requirements: 新規（Phase 15 - History-based Reranking）_

#### 15.6 BookmarkManagerサービスの実装

- [ ] 15.6.1 `BookmarkManager`クラスの基本構造を実装（`src/services/bookmark_manager.py`）
  - **実装内容**:
    ```python
    class BookmarkManager:
        def __init__(self, bookmark_storage: BookmarkStorage, search_service: SearchService):
            self.bookmark_storage = bookmark_storage
            self.search_service = search_service
    ```
  - **ファイル**: 新規作成 `src/services/bookmark_manager.py`
  - _Requirements: 新規（Phase 15 - Bookmark Service）_

- [ ] 15.6.2 ブックマーク作成機能を実装
  - **メソッド**: `create_bookmark(name: str, query: str, filters: Dict) -> SearchBookmark`
  - **処理**:
    1. UUIDを生成
    2. SearchBookmarkオブジェクトを作成
    3. BookmarkStorageに保存
    4. 作成されたブックマークを返す
  - **ファイル**: `src/services/bookmark_manager.py`
  - _Requirements: 新規（Phase 15 - Create Bookmark）_

- [ ] 15.6.3 ブックマーク実行機能を実装
  - **メソッド**: `execute_bookmark(bookmark_id: str) -> List[Dict]`
  - **処理**:
    1. ブックマークを読み込み
    2. SearchServiceで検索実行
    3. 使用回数をインクリメント
    4. last_usedを更新
    5. 検索結果を返す
  - **ファイル**: `src/services/bookmark_manager.py`
  - _Requirements: 新規（Phase 15 - Execute Bookmark）_

- [ ] 15.6.4 ブックマーク一覧取得機能を実装
  - **メソッド**: `list_bookmarks(sort_by: str = 'last_used') -> List[SearchBookmark]`
  - **ファイル**: `src/services/bookmark_manager.py`
  - _Requirements: 新規（Phase 15 - List Bookmarks）_

#### 15.7 MCPツールの実装

- [ ] 15.7.1 `create_project` MCPツールを実装
  - **ツール定義**:
    ```json
    {
      "method": "create_project",
      "params": {
        "name": "string",
        "description": "string",
        "tags": ["string"]
      }
    }
    ```
  - **ファイル**: `src/mcp/protocol_handler.py`
  - **メソッド**: `_tool_create_project(params: Dict) -> Dict`
  - **処理**: ProjectManager.create_projectを呼び出し
  - _Requirements: 新規（Phase 15 - MCP Tool）_

- [ ] 15.7.2 `list_projects` MCPツールを実装
  - **ツール定義**:
    ```json
    {
      "method": "list_projects",
      "params": {
        "sort_by": "string (optional)"
      }
    }
    ```
  - **ファイル**: `src/mcp/protocol_handler.py`
  - **メソッド**: `_tool_list_projects(params: Dict) -> Dict`
  - _Requirements: 新規（Phase 15 - MCP Tool）_

- [ ] 15.7.3 `update_project` MCPツールを実装
  - **ツール定義**:
    ```json
    {
      "method": "update_project",
      "params": {
        "project_id": "string",
        "name": "string (optional)",
        "description": "string (optional)",
        "tags": ["string"] "(optional)"
      }
    }
    ```
  - **ファイル**: `src/mcp/protocol_handler.py`
  - **メソッド**: `_tool_update_project(params: Dict) -> Dict`
  - _Requirements: 新規（Phase 15 - MCP Tool）_

- [ ] 15.7.4 `delete_project` MCPツールを実装
  - **ツール定義**:
    ```json
    {
      "method": "delete_project",
      "params": {
        "project_id": "string",
        "delete_memories": "boolean (optional)"
      }
    }
    ```
  - **ファイル**: `src/mcp/protocol_handler.py`
  - **メソッド**: `_tool_delete_project(params: Dict) -> Dict`
  - _Requirements: 新規（Phase 15 - MCP Tool）_

- [ ] 15.7.5 `search_in_project` MCPツールを実装
  - **ツール定義**:
    ```json
    {
      "method": "search_in_project",
      "params": {
        "project_id": "string",
        "query": "string",
        "top_k": "number (optional)"
      }
    }
    ```
  - **ファイル**: `src/mcp/protocol_handler.py`
  - **メソッド**: `_tool_search_in_project(params: Dict) -> Dict`
  - _Requirements: 新規（Phase 15 - MCP Tool）_

- [ ] 15.7.6 `create_bookmark` MCPツールを実装
  - **ツール定義**:
    ```json
    {
      "method": "create_bookmark",
      "params": {
        "name": "string",
        "query": "string",
        "filters": "object (optional)"
      }
    }
    ```
  - **ファイル**: `src/mcp/protocol_handler.py`
  - **メソッド**: `_tool_create_bookmark(params: Dict) -> Dict`
  - _Requirements: 新規（Phase 15 - MCP Tool）_

- [ ] 15.7.7 `execute_bookmark` MCPツールを実装
  - **ツール定義**:
    ```json
    {
      "method": "execute_bookmark",
      "params": {
        "bookmark_id": "string"
      }
    }
    ```
  - **ファイル**: `src/mcp/protocol_handler.py`
  - **メソッド**: `_tool_execute_bookmark(params: Dict) -> Dict`
  - _Requirements: 新規（Phase 15 - MCP Tool）_

- [ ] 15.7.8 `list_bookmarks` MCPツールを実装
  - **ツール定義**:
    ```json
    {
      "method": "list_bookmarks",
      "params": {
        "sort_by": "string (optional)"
      }
    }
    ```
  - **ファイル**: `src/mcp/protocol_handler.py`
  - **メソッド**: `_tool_list_bookmarks(params: Dict) -> Dict`
  - _Requirements: 新規（Phase 15 - MCP Tool）_

#### 15.8 main.pyの統合

- [ ] 15.8.1 main.pyにProjectManagerとBookmarkManagerを統合
  - **変更ファイル**: `src/main.py`
  - **追加内容**:
    ```python
    # init_services内で初期化
    project_storage = ProjectStorage(data_dir)
    bookmark_storage = BookmarkStorage(data_dir)

    project_manager = ProjectManager(project_storage, vector_db)
    bookmark_manager = BookmarkManager(bookmark_storage, search_service)

    # MCPProtocolHandlerに渡す
    handler = MCPProtocolHandler(
        ...,
        project_manager=project_manager,
        bookmark_manager=bookmark_manager
    )
    ```
  - _Requirements: 既存Requirement 11の拡張_

- [ ] 15.8.2 MCPProtocolHandlerのコンストラクタを更新
  - **変更ファイル**: `src/mcp/protocol_handler.py`
  - **変更内容**: `__init__`に`project_manager`と`bookmark_manager`パラメータを追加
  - _Requirements: 既存Requirement 11の拡張_

#### 15.9 CLIコマンドの追加

- [ ] 15.9.1 `project` CLIコマンドを実装
  - **コマンド**:
    ```bash
    python -m src.cli project list
    python -m src.cli project create --name "my-project" --description "..."
    python -m src.cli project delete --id "project-id"
    ```
  - **ファイル**: `src/cli.py`
  - **実装**: `cmd_project(args)`関数を追加
  - _Requirements: 既存Requirement 13の拡張_

- [ ] 15.9.2 `bookmark` CLIコマンドを実装
  - **コマンド**:
    ```bash
    python -m src.cli bookmark list
    python -m src.cli bookmark create --name "React Errors" --query "..."
    python -m src.cli bookmark run --id "bookmark-id"
    ```
  - **ファイル**: `src/cli.py`
  - **実装**: `cmd_bookmark(args)`関数を追加
  - _Requirements: 既存Requirement 13の拡張_

#### 15.10 テストの作成

- [ ] 15.10.1 ProjectManagerのユニットテストを作成
  - **ファイル**: 新規作成 `tests/unit/services/test_project_manager.py`
  - **テストケース**:
    - プロジェクト作成
    - プロジェクト一覧取得
    - プロジェクト更新
    - プロジェクト削除
    - 自動選択機能
  - **参照**: 既存の`test_ingestion.py`のパターン
  - _Requirements: Testing Strategy_

- [ ] 15.10.2 BookmarkManagerのユニットテストを作成
  - **ファイル**: 新規作成 `tests/unit/services/test_bookmark_manager.py`
  - **テストケース**:
    - ブックマーク作成
    - ブックマーク実行
    - ブックマーク一覧取得
    - 使用回数の記録
  - _Requirements: Testing Strategy_

- [ ] 15.10.3 ProjectStorageのユニットテストを作成
  - **ファイル**: 新規作成 `tests/unit/storage/test_project_storage.py`
  - **テストケース**:
    - JSON保存/読み込み
    - プロジェクト検索
    - エラーハンドリング
  - _Requirements: Testing Strategy_

- [ ] 15.10.4 E2Eテストを追加
  - **ファイル**: `tests/e2e/test_full_workflow.py`に追加
  - **テストケース**:
    - プロジェクト作成 → 会話取り込み → プロジェクト内検索
    - ブックマーク作成 → ブックマーク実行
  - _Requirements: Testing Strategy_

#### 15.11 ドキュメントの更新

- [ ] 15.11.1 README.mdを更新
  - **追加内容**:
    - プロジェクト管理機能の説明
    - 検索ブックマーク機能の説明
    - 使用例
  - **ファイル**: `README.md`
  - _Requirements: Requirement 13_

- [ ] 15.11.2 CLAUDE.mdを更新
  - **追加内容**:
    - ProjectManagerの実装詳細
    - BookmarkManagerの実装詳細
    - CLIコマンドの使用例
  - **ファイル**: `CLAUDE.md`
  - _Requirements: Requirement 13_

- [ ] 15.11.3 FEATURES_JA.mdを更新
  - **追加内容**:
    - プロジェクト管理機能の日本語説明
    - 使用例とユースケース
  - **ファイル**: `FEATURES_JA.md`
  - _Requirements: Requirement 13_

- [ ] 15.11.4 tasks.mdを更新
  - **内容**: Phase 15を完了としてマーク
  - **ファイル**: `.kiro/specs/dev-knowledge-orchestrator/tasks.md`
  - _Requirements: Requirement 13_

#### 15.12 パフォーマンステストの追加

- [ ] 15.12.1 プロジェクトフィルター検索のパフォーマンステスト
  - **ファイル**: `scripts/performance_profiler.py`に追加
  - **測定項目**:
    - プロジェクトフィルター適用時の検索速度
    - 複数プロジェクト環境での検索速度
  - _Requirements: Requirement 8_

---

## 実装の優先順位

### 高優先度（Week 1）
1. データモデル拡張（15.1.1〜15.1.3）
2. ストレージ層実装（15.2.1〜15.2.2）
3. ProjectManager基本機能（15.3.1〜15.3.5）
4. MCPツール実装（15.7.1〜15.7.5）
5. main.py統合（15.8.1〜15.8.2）

### 中優先度（Week 2）
6. SearchService拡張（15.5.1〜15.5.3）
7. BookmarkManager実装（15.6.1〜15.6.4）
8. MCPツール実装（15.7.6〜15.7.8）
9. ユニットテスト（15.10.1〜15.10.3）

### 低優先度（Week 3）
10. IngestionService拡張（15.4.1）
11. CLIコマンド追加（15.9.1〜15.9.2）
12. E2Eテスト（15.10.4）
13. ドキュメント更新（15.11.1〜15.11.4）
14. パフォーマンステスト（15.12.1）

---

## 依存関係グラフ

```
15.1 (データモデル)
  ↓
15.2 (ストレージ層)
  ↓
15.3 (ProjectManager) ← 15.4 (IngestionService拡張)
  ↓                    ↓
15.7.1-5 (MCP)    15.5 (SearchService拡張)
  ↓                    ↓
15.8 (main.py統合) ← 15.6 (BookmarkManager)
  ↓                    ↓
15.10 (テスト)    15.7.6-8 (MCP)
  ↓
15.11 (ドキュメント)
  ↓
15.12 (パフォーマンステスト)
```

---

## 成功基準

- [ ] すべてのユニットテストが通過
- [ ] E2Eテストが通過
- [ ] MCPクライアントから全ツールが呼び出し可能
- [ ] ドキュメントが完全更新済み
- [ ] パフォーマンステストで性能低下なし（検索速度 ≤200ms維持）

---

## 注意事項

1. **後方互換性**: 既存のAPIは変更しない（パラメータ追加はオプション引数のみ）
2. **エラーハンドリング**: すべての新機能に適切なエラーハンドリングを実装
3. **型ヒント**: すべてのメソッドに型ヒントを付ける
4. **ドキュメント**: docstringを必ず記載（Google Style）
5. **テスト**: 新機能にはテストを必ず追加

---

## 参考資料

- NotebookLM比較分析: `NOTEBOOKLM_COMPARISON_ANALYSIS.md`
- 既存実装パターン: `src/services/ingestion.py`, `src/services/search.py`
- データモデル: `src/models/__init__.py`
- MCPツール実装: `src/mcp/protocol_handler.py`
