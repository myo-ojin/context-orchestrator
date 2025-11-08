# NotebookLM Skill vs Context Orchestrator - 比較分析レポート

## 分析日時
2025-01-15

## 1. プロジェクト思想の類似性 🎯

### 共通の目標
両プロジェクトは**「開発者の知識を保存・検索・活用する」**という同じ目的を持つ

| 側面 | NotebookLM Skill | Context Orchestrator |
|-----|------------------|---------------------|
| **目的** | ドキュメントベースの知識検索 | 会話ベースの経験記録・検索 |
| **価値** | ソースに基づいた信頼性の高い回答 | 過去の解決策の即座の発見 |
| **ユーザー** | Claude Codeユーザー | Claude CLI/MCP対応クライアント |
| **設計思想** | セットアップの簡素化 | プライバシー重視・ローカル優先 |

---

## 2. アーキテクチャの違い 🏗️

### NotebookLM Skill（スキルベース）
```
Claude Code
  ↓ スキルフォルダー (~/.claude/skills/notebooklm/)
  ↓ SKILL.md（プロンプト）
Python Scripts
  ↓ Patchright（ブラウザ自動化）
Google NotebookLM（外部サービス）
  ↓ Gemini 2.5（処理）
  ↓ 回答（引用付き）
Claude Code
```

**特徴**:
- **ステートレス**: 各クエリが独立
- **外部依存**: NotebookLM/Geminiに依存
- **ブラウザ自動化**: Chromeを操作
- **セットアップ5分**

### Context Orchestrator（MCPサーバーベース）
```
MCPクライアント（Claude Desktop/Cursor/CLI）
  ↓ stdio JSON-RPC
MCP Protocol Handler
  ↓ サービス層
IngestionService / SearchService / ConsolidationService
  ↓ ストレージ層
Chroma DB（ベクトル） + BM25 Index（キーワード）
  ↓ モデル層
Ollama（ローカルLLM） ± クラウドLLM
  ↓ 回答
MCPクライアント
```

**特徴**:
- **ステートフル**: メモリ階層（作業→短期→長期）
- **完全ローカル**: すべて自己完結
- **MCPプロトコル**: 標準規格
- **セットアップ30分**

---

## 3. 参考にできる実装技術 💡

### ✅ 3.1 データ永続化戦略

**NotebookLM Skillの実装**:
```
data/
├── library.json          # ノートブックメタデータ
├── auth_info.json        # 認証情報
└── browser_state/        # ブラウザセッション
```

**Context Orchestratorへの適用**:
```python
# 現在の実装
~/.context-orchestrator/
├── chroma_db/           # ベクトルDB
├── bm25_index.pkl       # BM25インデックス
├── last_consolidation   # タイムスタンプ
└── app.log              # ログ

# 追加できる構造（NotebookLMスタイル）
~/.context-orchestrator/
├── library/
│   ├── projects.json    # プロジェクトメタデータ
│   ├── tags.json        # タグ管理
│   └── bookmarks.json   # よく使う検索
├── sessions/
│   └── active_context.json  # アクティブセッション
└── config/
    └── user_preferences.json  # ユーザー設定
```

**取り入れるべきアイデア**:
- ✅ JSONベースのメタデータ管理
- ✅ プロジェクト/タグによる階層化
- ✅ よく使う検索のブックマーク機能

---

### ✅ 3.2 スマートなライブラリ管理

**NotebookLM Skillのアプローチ**:
```python
# 3つのモード
1. Smart Add: ノートブックに問い合わせて内容を把握してから登録
2. Manual Add: ユーザーが名前・トピックを提供
3. Query Mode: コンテキストに基づいて自動選択
```

**Context Orchestratorへの適用**:
```python
# 現在: すべての会話を単一のDBに保存

# 改善案: プロジェクト別管理
class ProjectManager:
    """プロジェクト別に記憶を管理"""

    def add_project(self, name: str, description: str, tags: List[str]):
        """新しいプロジェクトを登録"""
        pass

    def auto_select_project(self, query: str) -> Optional[str]:
        """クエリから関連プロジェクトを自動選択"""
        pass

    def search_in_project(self, project_id: str, query: str):
        """特定プロジェクト内で検索"""
        pass
```

**メリット**:
- 検索精度の向上（関係ない記憶を除外）
- メモリ使用量の削減
- プロジェクト単位のエクスポート/インポート

---

### ✅ 3.3 ユーザーインタラクションの改善

**NotebookLM Skillの工夫**:
```python
# フォローアップメカニズム
query = f"{user_question}\n\nIs that ALL you need?"

# 人間らしい操作
- タイピング速度をランダム化
- マウス移動のシミュレーション
- 自然な遅延の挿入
```

**Context Orchestratorへの適用**:
```python
# MCPツールの改善案

def search_memory_interactive(
    query: str,
    clarify: bool = True  # 追加パラメータ
) -> Dict[str, Any]:
    """対話的な検索"""

    results = search_service.search(query)

    if clarify and len(results) > 5:
        # 結果が多い場合、絞り込みを提案
        suggestions = _generate_refinement_suggestions(results)
        return {
            'results': results[:3],
            'suggestions': suggestions,
            'message': '結果が多いため上位3件のみ表示。絞り込みますか？'
        }

    return {'results': results}
```

**メリット**:
- ユーザーフレンドリーな体験
- 検索精度の向上
- 無駄なトークン消費の削減

---

### ✅ 3.4 セッション状態の賢い管理

**NotebookLM Skillのアプローチ**:
```python
# ステートレスだが、メタデータは永続化
- ブラウザ状態をキャッシュ（再認証不要）
- ノートブックライブラリを保存（毎回の選択不要）
- 使用履歴を記録（よく使うものを優先）
```

**Context Orchestratorへの適用**:
```python
# 現在の実装
class SessionManager:
    """セッション管理（Phase 6）"""
    # 実装済みだが、使用履歴の活用が不十分

# 改善案: 使用履歴の活用
class SmartSessionManager:
    def __init__(self):
        self.usage_history = {}  # schema_type別の使用頻度

    def record_usage(self, memory_id: str, schema_type: str):
        """使用履歴を記録"""
        self.usage_history[schema_type] = \
            self.usage_history.get(schema_type, 0) + 1

    def suggest_schema_filter(self, query: str) -> Optional[str]:
        """よく使うスキーマを提案"""
        if 'エラー' in query or 'バグ' in query:
            return 'Incident'  # 過去の履歴から推測
        return None
```

**メリット**:
- 検索の高速化
- ユーザーの使い方に適応
- 関連性の高い結果を優先

---

## 4. アーキテクチャ上の違いの分析 🔍

### ステートレス vs ステートフル

| 側面 | NotebookLM (ステートレス) | Context Orchestrator (ステートフル) |
|-----|--------------------------|-----------------------------------|
| **メリット** | シンプル、障害に強い | 文脈を保持、段階的な改善 |
| **デメリット** | 毎回初期化、効率低い | 複雑、状態管理が必要 |
| **適用場面** | 単発の質問 | 継続的な開発作業 |

**取り入れるべきアイデア**:
- ✅ Context Orchestratorは基本ステートフルだが、**ステートレスモード**も提供
- ✅ 軽量な質問には高速なステートレス検索を使用
- ✅ 複雑な探索にはステートフルな会話履歴を活用

---

### 外部サービス依存 vs 完全ローカル

| 側面 | NotebookLM (外部依存) | Context Orchestrator (ローカル) |
|-----|-----------------------|--------------------------------|
| **メリット** | 高性能（Gemini 2.5）、メンテ不要 | プライバシー、オフライン可 |
| **デメリット** | レート制限、コスト、プライバシー | セットアップ複雑、性能制限 |
| **インフラ** | なし | Ollama必須 |

**ハイブリッドアプローチの提案**:
```python
class HybridSearchService:
    """ローカル優先、必要に応じて外部サービス利用"""

    def search(self, query: str, mode: str = 'auto'):
        # mode = 'local' | 'cloud' | 'auto'

        if mode == 'local' or (mode == 'auto' and self._is_simple_query(query)):
            # ローカルで高速検索
            return self.local_search(query)
        else:
            # 複雑なクエリはクラウドLLMで処理
            return self.cloud_enhanced_search(query)
```

---

## 5. 実装すべき新機能の提案 🚀

### 優先度：高

#### 5.1 プロジェクト管理機能
```python
# 新規MCP Tool: create_project
{
  "method": "create_project",
  "params": {
    "name": "my-react-app",
    "description": "React + TypeScript project",
    "tags": ["react", "typescript", "frontend"]
  }
}

# 新規MCP Tool: search_in_project
{
  "method": "search_in_project",
  "params": {
    "project": "my-react-app",
    "query": "React hooks error handling"
  }
}
```

**実装ファイル**: `src/services/project_manager.py`

#### 5.2 検索ブックマーク機能
```python
# 新規MCP Tool: save_search_bookmark
{
  "method": "save_search_bookmark",
  "params": {
    "name": "React Errors",
    "query": "React hooks エラー処理",
    "filters": {"schema_type": "Incident"}
  }
}

# 新規MCP Tool: use_bookmark
{
  "method": "use_bookmark",
  "params": {"name": "React Errors"}
}
```

**実装ファイル**: `src/services/bookmark_manager.py`

#### 5.3 使用履歴の活用
```python
# SearchServiceの拡張
class SearchService:
    def search_with_history(self, query: str):
        """使用履歴を考慮した検索"""

        # 1. 過去の検索パターンを分析
        similar_past_queries = self._find_similar_queries(query)

        # 2. よくアクセスされる記憶を優先
        boost_memory_ids = self._get_frequently_accessed()

        # 3. 検索実行
        results = self.search(query)

        # 4. 履歴に基づいてリランキング
        return self._rerank_with_history(results, boost_memory_ids)
```

**実装ファイル**: `src/services/search.py`（拡張）

---

### 優先度：中

#### 5.4 対話的な絞り込み
```python
# SearchServiceの拡張
def search_interactive(
    query: str,
    auto_refine: bool = True
) -> Dict[str, Any]:
    """対話的な検索"""

    results = self.search(query)

    if auto_refine and len(results) > 10:
        # スキーマ別の分布を分析
        schema_distribution = self._analyze_schema_distribution(results)

        return {
            'results': results[:5],
            'total': len(results),
            'schema_distribution': schema_distribution,
            'suggestions': [
                f"Incidentのみに絞り込む（{schema_distribution['Incident']}件）",
                f"Snippetのみに絞り込む（{schema_distribution['Snippet']}件）"
            ]
        }

    return {'results': results}
```

---

### 優先度：低

#### 5.5 ステートレス検索モード
```python
# 新規MCP Tool: quick_search（キャッシュなし、高速）
{
  "method": "quick_search",
  "params": {"query": "Python type hints"}
}
```

**用途**: 単発の質問、CI/CD統合、スクリプトからの呼び出し

---

## 6. 実装ロードマップ 📅

### Phase 15: プロジェクト管理（1週間）
- [ ] ProjectManager実装
- [ ] create_project / list_projects MCPツール
- [ ] search_in_project機能
- [ ] プロジェクト別エクスポート/インポート

### Phase 16: 検索の改善（1週間）
- [ ] BookmarkManager実装
- [ ] 使用履歴の記録
- [ ] 履歴ベースのリランキング
- [ ] 対話的な絞り込み

### Phase 17: パフォーマンス最適化（数日）
- [ ] quick_search（ステートレスモード）
- [ ] キャッシュ戦略の最適化
- [ ] インデックスの最適化

---

## 7. 取り入れないもの ❌

### ブラウザ自動化
**理由**:
- Context Orchestratorはローカル完結が設計思想
- ブラウザ自動化は外部サービス依存
- Patchrightの依存は複雑さを増す

### 完全なステートレス化
**理由**:
- メモリ階層（作業→短期→長期）が核心的価値
- 統合・忘却機能が差別化要因
- ステートレスモードは**オプション**として提供

---

## 8. まとめ 📝

### NotebookLM Skillから学ぶべき点

| 要素 | 採用すべき理由 | 実装優先度 |
|-----|--------------|-----------|
| **プロジェクト管理** | 検索精度向上 | 🔴 高 |
| **検索ブックマーク** | ユーザー体験改善 | 🔴 高 |
| **使用履歴活用** | 適応的な検索 | 🟡 中 |
| **対話的絞り込み** | UX向上 | 🟡 中 |
| **ステートレスモード** | 特定用途で有用 | 🟢 低 |

### Context Orchestratorの強み（保持すべき）

- ✅ 完全ローカル・プライバシー重視
- ✅ MCPプロトコル標準対応
- ✅ メモリ階層による段階的改善
- ✅ 自動統合・忘却機能
- ✅ ハイブリッド検索（ベクトル+BM25）

### 次のアクション

1. **新ブランチ作成**: `claude/add-project-management-[session-id]`
2. **Phase 15実装**: ProjectManager + 関連MCPツール
3. **Phase 16実装**: 検索改善（ブックマーク、履歴）
4. **ドキュメント更新**: 新機能の説明

---

**結論**: NotebookLM Skillのシンプルさ・使いやすさを参考にしつつ、Context Orchestratorの完全ローカル・プライバシー重視の設計思想は維持する。プロジェクト管理と検索改善を優先的に実装することで、両者の良いとこ取りを実現する。
