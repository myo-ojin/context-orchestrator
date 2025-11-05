# Requirements Document - 外部脳システム

## Introduction

本システムは、開発者個人の実務経験と知識を外部化し、人間の脳の記憶システムを模倣した「第二の脳」を構築する。単なる検索可能な知識ベースではなく、経験を記録し、記憶を関連付け、自発的に想起し、効率的に忘却する、生きた記憶装置である。

中間層としてContext Orchestratorを配置し、MCPサーバとして振る舞うことで、任意のLLMクライアント（Claude、GPT、Cursor、VS Code拡張など）から統一的にアクセス可能にする。推論・要約・埋め込み・再ランクはローカルのオープンウェイトLLMで実行し、コストとプライバシーを両立させる。

## Core Philosophy

**「使うほど賢くなる、自分専用の外部脳」**

- 経験を自動的に記録し、構造化する
- 記憶同士を関連付け、知識グラフを構築する
- 文脈に応じて自発的に過去の記憶を想起する
- 重要な記憶を保持し、不要な記憶を効率的に忘却する
- 人間の脳のように、作業記憶・短期記憶・長期記憶の階層を持つ

## Phase Classification



- **MVP (Phase 1)**: 要件 1-13（コア機能と初期忘却）

- **Phase 2**: 要件 21-26（高度な記憶機能と文脈想起）

- **Future (Optional)**: 外部検索統合、マルチユーザー対応



## Glossary

### システムコンポーネント
- **Context Orchestrator**: MCPサーバとして動作し、記憶の管理・想起・忘却を担う中間レイヤ
- **MCP (Model Context Protocol)**: 上位LLMクライアントと下位ストレージ層の間の標準プロトコル
- **MCP Client**: Claude、GPT、Cursor、VS Code拡張など、MCPプロトコルを使用してContext Orchestratorに接続する上位アプリケーション
- **Memory Consolidator**: 記憶の統合・圧縮・忘却を実行するコンポーネント
- **Model Router**: タスクの複雑度とコストに基づいて、適切なLLMモデル（ローカル/クラウド）を選択するコンポーネント

### 記憶の階層
- **Working Memory**: 現在進行中のタスクの文脈を保持する作業記憶（数時間保持）
- **Short-term Memory**: 最近の経験を保持する短期記憶（数日〜数週間保持）
- **Long-term Memory**: 重要な知識を永続的に保持する長期記憶
- **Memory Cluster**: 類似した記憶をまとめたグループ
- **Representative Memory**: クラスタ内で代表として選ばれた記憶

### 記憶のスキーマ
- **Incident**: 不具合・原因・再現手順・修正PRなどを含む問題解決の記憶
- **Snippet**: コード片と使用理由を含むコード記憶
- **Decision**: 選択肢・判断根拠・トレードオフを含む意思決定の記憶
- **Process**: 思考プロセス、試行錯誤、学びを含む思考の記憶

### 記憶の属性
- **refs**: 元の出典URL、ファイルパス、コミットIDなどの参照情報
- **Memory Strength**: 記憶の強度（時間減衰と参照ブーストで変動）
- **Importance Score**: 記憶の重要度スコア（保持・削除の判定に使用）
- **Embedding**: 記憶の埋め込みベクトル（意味的類似性の計算に使用）

### 検索と想起
- **Retriever**: クエリに基づいて候補群を収集する検索コンポーネント
- **Hybrid Search**: ベクトル検索（意味的類似性）とBM25検索（キーワードマッチ）を組み合わせた検索手法
- **Re-ranking**: 検索結果を整合度・信頼性・最近度・自己一致性などの基準で再評価して順序を最適化する処理
- **Proactive Recall**: 文脈に基づいて自発的に関連記憶を想起する機能

### データ構造
- **Chunk**: 意味的な単位（見出し単位、関数単位など）で分割されたデータの断片
- **Vector Index**: 埋め込みベクトルを格納し、意味的類似性に基づく検索を可能にする索引（Chroma、Qdrantなど）
- **BM25 Index**: キーワードベースの全文検索を可能にする索引
- **Memory Graph**: 記憶同士の関連性を表すグラフ構造

### Obsidian統合
- **Vault**: Obsidianの知識ベース全体
- **Wikilink**: Obsidianの内部リンク記法 `[[ファイル名]]`
- **Backlink**: 逆方向のリンク（どのファイルから参照されているか）

### 忘却機能
- **Forgetting Curve**: エビングハウスの忘却曲線（時間経過による記憶の減衰）
- **Memory Decay**: 時間経過による記憶強度の減衰
- **Compression Level**: 記憶の圧縮レベル（Level 0: 生データ、Level 1: 要約、Level 2: エッセンス、Level 3: アーカイブ）

### ストレージとインフラ
- **Chroma**: SQLiteベースのベクトルデータベース（ローカルファイルに保存、セットアップ不要）
- **Ollama**: ローカルLLMの実行環境（モデル管理とAPI提供）
- **tiktoken**: OpenAI互換のトークナイザー（テキストのトークン数計算に使用）
- **Q4_K_M**: 4bit量子化形式（モデルサイズを約1/4に圧縮、実用的な精度を維持）

---

## MVP Requirements (Phase 1)

以下の要件は、最初のリリース（MVP）で実装する必須機能である。

### Requirement 1 (MVP) - CLI会話の透過的な自動記録

**User Story:** 開発者として、claude/codex CLIを普通に使うだけで、自動的に会話が記録されることを期待する。特別な操作は不要で、透過的に動作し、元のコマンドと完全に同じ挙動を保つ。

#### Acceptance Criteria

1. WHEN システムがセットアップされる, THE System SHALL PowerShellプロファイルにclaude/codex関数を自動的に追加する
2. WHEN 開発者がPowerShellを起動する, THE System SHALL 自動的にclaude/codex関数を有効化し、元のコマンドをラップする
3. WHEN 開発者が `claude` または `codex` コマンドを任意の引数で実行する, THE System SHALL 透過的に出力をキャプチャし、バックグラウンドでContext Orchestratorに送信する
4. WHEN Context Orchestratorが起動していない, THE System SHALL エラーを表示せず、通常通り動作する
5. WHEN 会話が記録される, THE System SHALL バックグラウンドジョブで処理し、ユーザー体験を妨げない
6. WHEN 元のコマンドがエラーを返す, THE System SHALL 終了コードとエラーメッセージをそのまま保持する
7. WHEN パイプライン入力が使用される, THE System SHALL パイプライン入力を正しく処理する

#### 技術実装の詳細

**セットアップスクリプト:**
```powershell
# setup-cli-recording.ps1
# PowerShell $PROFILE に関数を自動追加
# 一度だけ実行すれば永続的に有効
```

**ラッパー関数の実装:**
```powershell
function claude {
    [CmdletBinding()]
    param([Parameter(ValueFromRemainingArguments=$true)]$args)
    
    # 元のコマンドを実行し、出力をキャプチャ
    # Tee-Objectで画面表示とファイル保存を同時実行
    # バックグラウンドジョブでContext Orchestratorに送信
    # エラーハンドリングで完全互換性を保証
}
```

**動作の流れ:**
1. ユーザーが `claude "質問"` を実行
2. ラッパー関数が元のclaudeコマンドを呼び出す
3. 出力をTee-Objectでキャプチャ（ユーザーには通常通り表示）
4. バックグラウンドジョブでContext Orchestrator APIに送信
5. 一時ファイルを削除

**完全互換性の保証:**
- 全ての引数が正しく渡される（`--help`, `--search`, `--config`等）
- パイプライン入力が動作する（`echo "question" | claude`）
- 終了コードが保持される
- エラーメッセージがそのまま表示される
- Context Orchestratorが起動していなくても動作する

**利点:**
- ユーザーは何も意識しない
- 既存のワークフローを変えない
- 自動的に全て記録される
- 元のコマンドと完全に同じ挙動

**堅牢化された実装（推奨）:**

追加機能：
- **環境変数での設定**: `$env:ORCH_URL`, `$env:ORCH_TOKEN`
- **オフラインキュー + 自動再送**: ネットワーク障害時もキューに保存、指数バックオフで最大5回リトライ
- **機密情報の自動マスキング**: APIキー、トークン、パスワードを `[REDACTED]` に置換
- **容量制限**: 出力を1MBに切り詰め、SHA256ハッシュで識別
- **再帰防止**: `$env:EBR_INVOKING` フラグで無限ループ回避
- **詳細なメタデータ**: 実行時間、終了コード、ホスト情報を記録
- **stderr キャプチャ**: `2>&1` でエラー出力も記録

セキュリティとプライバシー：
- 機密情報の自動マスキング
- ローカルキューで安全に保存
- Bearer認証対応
- 容量制限でメモリ保護

### Requirement 1.5 (MVP) - Obsidian会話ログの取り込み

**User Story:** 開発者として、Obsidianに手動でコピーした会話ログも自動的に検出して記録したい。これにより、CLI以外のツール（Claude Desktop、ブラウザ版等）の会話も記憶できる。

#### Acceptance Criteria

1. WHEN 開発者がObsidian Vaultに会話形式のノートを作成する, THE Context Orchestrator SHALL ファイルシステム監視を通じて自動的に検出する
2. WHEN ノートが会話形式（`**User:**` と `**Assistant:**` のパターン）を含む, THE Context Orchestrator SHALL 会話として認識する
3. WHEN 会話を抽出する, THE Context Orchestrator SHALL ユーザーメッセージとアシスタント応答をペアで構造化する
4. WHEN Wikilinkを検出する, THE Context Orchestrator SHALL リンク先のファイルも関連情報として記録する
5. WHEN 会話ノートが更新される, THE Context Orchestrator SHALL 差分のみを新しい記憶として追加する

#### 技術実装の詳細

**ファイルシステム監視:**
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ObsidianConversationWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            self.process_file(event.src_path)
```

**会話形式の検出:**
```python
conversation_pattern = re.compile(
    r'\*\*User:\*\*\s*(.*?)\s*\*\*Assistant:\*\*\s*(.*?)(?=\*\*User:\*\*|\Z)',
    re.DOTALL
)
```

**参考記事の形式に対応:**
- CLAUDE.mdのスケジュールファイル
- 情報提供依頼書
- 調査依頼書
- エラーログ

### Requirement 1.6 (MVP) - Kiro自身の会話記録

**User Story:** 開発者として、Kiro（このツール）での会話を自動的に記録したい。これにより、Kiroを使うだけで外部脳が成長する。

#### Acceptance Criteria

1. WHEN 開発者がKiroで会話する, THE Context Orchestrator SHALL 全ての会話内容を自動的に記録する
2. WHEN 会話のターンが完了する, THE Context Orchestrator SHALL ユーザーメッセージ、アシスタント応答、文脈を記録する
3. WHEN タスクを実行する, THE Context Orchestrator SHALL 参照したファイル、実行したコマンド、結果を記録する
4. WHEN 会話が終了する, THE Context Orchestrator SHALL 会話全体を構造化して記憶として保存する
5. WHEN 記憶を保存する, THE Context Orchestrator SHALL 自動的にIncident、Snippet、Decision、Processのいずれかに分類する

#### 技術実装の詳細

**内部API統合:**
```python
class KiroConversationCollector:
    def on_conversation_turn(self, user_message, assistant_message, context):
        conversation_data = {
            'timestamp': datetime.now().isoformat(),
            'user': user_message,
            'assistant': assistant_message,
            'context': {
                'files': context.get('files', []),
                'workspace': context.get('workspace'),
                'task': context.get('task')
            }
        }
        self.orchestrator.ingest_conversation(conversation_data)
```

### Requirement 2 (MVP) - 記憶のスキーマ正規化

**User Story:** 開発者として、取り込まれた経験がIncident、Snippet、Decision、Processといったドメイン特化スキーマに正規化され、元の出典情報（refs）が必ず結び付けられることを期待する。これにより、後から検証可能な形で記憶が構造化される。

#### Acceptance Criteria

1. WHEN Context Orchestrator がイベントを受信する, THE Context Orchestrator SHALL イベント内容を言語処理してIncident、Snippet、Decision、Processのいずれかのスキーマに分類する
2. WHEN Context Orchestrator がイベントをスキーマに正規化する, THE Context Orchestrator SHALL 元の出典URL、ファイルパス、コミットIDをrefsフィールドに記録する
3. WHEN Context Orchestrator がIncidentスキーマを生成する, THE Context Orchestrator SHALL 不具合内容、原因、再現手順、修正PR、解決策を含める
4. WHEN Context Orchestrator がSnippetスキーマを生成する, THE Context Orchestrator SHALL コード片、使用理由、適用コンテキスト、関連技術を含める
5. WHEN Context Orchestrator がDecisionスキーマを生成する, THE Context Orchestrator SHALL 選択肢、判断根拠、トレードオフ、結果、学びを含める
6. WHEN Context Orchestrator がProcessスキーマを生成する, THE Context Orchestrator SHALL 思考プロセス、試行錯誤、失敗した試み、最終的な学びを含める

### Requirement 3 (MVP) - 記憶のチャンク化と索引化

**User Story:** 開発者として、正規化された記憶がチャンク化・要約・エンティティ抽出され、メタデータ付きでハイブリッド検索用の索引に登録されることを期待する。これにより、効率的な検索と想起が可能になる。

#### Acceptance Criteria

1. WHEN Context Orchestrator が正規化された記憶を処理する, THE Context Orchestrator SHALL tiktokenトークナイザーを使用してデータを意味的な単位（Markdownの見出し単位、関数単位など）で512トークン以下のチャンクに分割する
2. WHEN Context Orchestrator がMarkdownを分割する, THE Context Orchestrator SHALL 見出し（`#`, `##`）を優先的な分割ポイントとし、512トークンを超える場合は段落単位で分割する
3. WHEN Context Orchestrator がコードブロックを処理する, THE Context Orchestrator SHALL コードブロックを分割せず、1つのチャンクとして保持する
4. WHEN Context Orchestrator がチャンクを生成する, THE Context Orchestrator SHALL ローカルLLMを使用して各チャンクの100トークン以下の要約を生成する
5. WHEN Context Orchestrator がチャンクを処理する, THE Context Orchestrator SHALL エンティティ（技術名、エラーコード、プロジェクト名など）を抽出して構造化データとして保存する
6. WHEN Context Orchestrator がメタデータを付与する, THE Context Orchestrator SHALL タグ、ISO 8601形式の日時、プロジェクト識別子、関連エラーコード、記憶強度を含める
7. WHEN Context Orchestrator がチャンクを索引化する, THE Context Orchestrator SHALL ベクトル索引（Chroma）とBM25索引の両方に5秒以内に登録を完了する

#### 技術実装の詳細

**トークナイザー:**
- tiktoken（GPT互換、標準的）を使用
- 512トークン = 約2,000文字（日本語）

**分割ロジック:**
1. Markdownの見出し（`#`, `##`, `###`）で優先的に分割
2. 512トークン超過時は段落（`\n\n`）で分割
3. コードブロック（` ```...``` `）は分割しない
4. 会話ログは1ターン（User + Assistant）を1チャンクとする

### Requirement 4 (MVP) - 作業記憶（Working Memory）

**User Story:** 開発者として、現在進行中のタスクの文脈を作業記憶に保持し、中断しても再開できるようにしたい。これにより、タスクの連続性が保たれる。

#### Acceptance Criteria

1. WHEN 開発者がタスクを開始する, THE Context Orchestrator SHALL ワーキングメモリセッションを作成し、タスクの文脈を記録する
2. WHEN タスクが進行中である, THE Context Orchestrator SHALL 作業内容、参照したファイル、実行したコマンドをワーキングメモリに追記する
3. WHEN タスクが中断される, THE Context Orchestrator SHALL 現在の文脈をワーキングメモリに保存し、再開用のチェックポイントを作成する
4. WHEN タスクを再開する, THE Context Orchestrator SHALL ワーキングメモリから文脈を復元し、「前回の続き」を可能にする
5. WHEN タスクが完了する, THE Context Orchestrator SHALL ワーキングメモリの内容を短期記憶に移行し、ワーキングメモリをクリアする
6. WHEN ワーキングメモリが8時間以上経過する, THE Context Orchestrator SHALL 自動的に短期記憶に移行する

**注記:** 保持期間（8時間）は初期値であり、実験と改善を通じて最適化する必要がある。

### Requirement 5 (MVP) - 記憶のクラスタリングと代表記憶

**User Story:** 開発者として、類似した記憶を自動的にクラスタリングし、代表記憶を選択して冗長性を排除したい。これにより、メモリ効率が向上し、検索結果が整理される。

#### Acceptance Criteria

1. WHEN Context Orchestrator が新しい記憶を保存する, THE Context Orchestrator SHALL 既存の記憶との類似度（コサイン類似度）を計算する
2. WHEN 類似度が0.9以上の記憶を検出する, THE Context Orchestrator SHALL それらをMemory Clusterにまとめる
3. WHEN Memory Clusterを作成する, THE Context Orchestrator SHALL 最も詳細または最新の記憶を代表記憶（Representative Memory）として選択する
4. WHEN 代表記憶を選択する, THE Context Orchestrator SHALL 他のメンバー記憶を圧縮し、差分情報のみを保存する
5. WHEN クラスタ化された記憶を検索する, THE Context Orchestrator SHALL 代表記憶を返し、「他に類似した記憶が X 件あります」と通知する

**注記:** 類似度閾値（0.9）は初期値であり、実験と改善を通じて最適化する必要がある。設定ファイルで調整可能とする。

### Requirement 6 (MVP) - 記憶の統合処理（Memory Consolidation）

**User Story:** 開発者として、1日の終わりに記憶を自動的に整理・統合し、作業記憶を短期記憶に移行したい。これにより、記憶が整理され、効率的に保存される。

#### Acceptance Criteria

1. WHEN 深夜3:00 AM（または手動トリガー）に, THE Memory Consolidator SHALL 統合処理を開始する
2. WHEN 統合処理を実行する, THE Memory Consolidator SHALL 完了したワーキングメモリを短期記憶に移行する
3. WHEN 統合処理を実行する, THE Memory Consolidator SHALL 短期記憶内の類似記憶をクラスタリングする
4. WHEN 統合処理を実行する, THE Memory Consolidator SHALL 重複を検出して統合し、代表記憶を選択する
5. WHEN 統合処理が完了する, THE Memory Consolidator SHALL 処理結果（クラスタ数、圧縮数、削除数）をログに記録する
6. WHEN 手動トリガーが実行される, THE System SHALL `context-orchestrator consolidate` コマンドで統合処理を開始する

**注記:** 統合処理の時刻（深夜3:00 AM）は初期値であり、セットアップ時に設定可能とする。実験と改善を通じて最適化する必要がある。

### Requirement 7 (MVP) - 効率的な忘却（時間ベース）

**User Story:** 開発者として、古い記憶を自動的に削除または圧縮し、メモリ使用量を制御したい。これにより、システムが長期的に効率的に動作する。

#### Acceptance Criteria

1. WHEN 記憶が30日以上経過する, THE Context Orchestrator SHALL 記憶の重要度スコアを評価する
2. WHEN 重要度スコアが0.3以下である, THE Context Orchestrator SHALL 記憶を削除候補としてマークする
3. WHEN 記憶が削除候補である, THE Context Orchestrator SHALL 記憶を圧縮（Level 1: 要約のみ保存）するか、完全に削除する
4. WHEN 記憶を削除する, THE Context Orchestrator SHALL 削除前に最終確認を行い、refs情報は保持する
5. WHEN メモリ使用量が閾値を超える, THE Context Orchestrator SHALL 緊急統合処理を実行し、古い記憶を積極的に削除する

**注記:** 経過日数（30日）と重要度スコア閾値（0.3）は初期値であり、実験と改善を通じて最適化する必要がある。設定ファイルで調整可能とする。

### Requirement 8 (MVP) - ハイブリッド検索と想起

**User Story:** 開発者として、どのLLMクライアントから質問しても、Context Orchestratorのハイブリッド検索経由で統一的に記憶を想起できることを期待する。これにより、ツールを変えても同じ外部脳にアクセスできる。

#### Acceptance Criteria

1. WHEN 開発者がMCPクライアントから質問を送信する, THE Context Orchestrator SHALL MCPプロトコル仕様に準拠したsearch()リクエストを2秒以内に受信して処理を開始する
2. WHEN Retriever がクエリを受け取る, THE Retriever SHALL ローカルLLM（nomic-embed-text）を使用してクエリの埋め込みベクトルを生成する
3. WHEN Retriever が候補群を収集する, THE Retriever SHALL ベクトル検索（Chroma DB）とBM25検索の結果を統合し、上位50件の候補を抽出する
4. WHEN Retriever が候補群を整理する, THE Retriever SHALL ルールベースの再ランキング（記憶強度、refsの信頼性、最近度、キーワードマッチ、ベクトル類似度）で順序を整えて上位10件を選択する
5. WHEN 検索結果を返す, THE Context Orchestrator SHALL 記憶の内容、refs、関連記憶へのリンクを含めて上位LLMへ返す

**注記:** 
- 処理時間目標（2秒）は通常200ms程度で完了し、大量データや複雑なクエリで最大2秒となる。
- 候補数（50件）と結果数（10件）は初期値であり、実験と改善を通じて最適化する必要がある。設定ファイルで調整可能とする。

#### 技術実装の詳細

**検索の流れ:**
1. クエリの埋め込み生成（ローカルLLM: nomic-embed-text）: 約50ms
2. ベクトル検索（Chroma DB）: 約10ms
3. BM25検索（Pythonライブラリ）: 約5ms
4. 結果のマージ（上位50件）: 約5ms
5. ルールベース再ランキング（上位10件）: 約10ms
6. **合計: 約80ms（高速）**

**再ランキングのスコア計算:**
```python
score = (
    memory.strength * 0.3 +           # 記憶強度
    recency_score * 0.2 +             # 最近度
    len(memory.refs) * 0.1 +          # refs信頼性
    memory.bm25_score * 0.2 +         # キーワードマッチ
    memory.vector_similarity * 0.2    # ベクトル類似度
)
```

**プライバシー保護:**
- 検索クエリは完全ローカル処理
- クラウドLLMには送信しない

### Requirement 9 (MVP) - Obsidian Vault統合

**User Story:** 開発者として、Obsidian Vaultを自律的に探索し、Wikilinkで関連ドキュメントを結びつけながら、記憶を構築したい。これにより、既存の知識ベースと外部脳が統合される。

#### Acceptance Criteria

1. WHEN Context Orchestrator がタスクを実行する, THE Context Orchestrator SHALL Obsidian Vault内を自律的に検索し、関連ファイルを発見する
2. WHEN 関連ドキュメントを発見する, THE Context Orchestrator SHALL Wikilink記法 `[[ファイル名]]` で参照を記録する
3. WHEN Wikilinkを検出する, THE Context Orchestrator SHALL リンク先のファイルを読み込み、記憶の関連付けを行う
4. WHEN バックリンクを検出する, THE Context Orchestrator SHALL 記憶の重要度スコアに反映する（多くのファイルから参照されている = 重要）
5. WHEN Obsidianノートを更新する, THE Context Orchestrator SHALL YAML frontmatter（tags、date、updated）を自動的に付与する

### Requirement 10 (MVP) - ハイブリッドモデルルーティング

**User Story:** 開発者として、タスクの複雑度とコストに基づいて、ローカルの軽量モデルとユーザー契約のクラウドLLMを動的に使い分けたい。これにより、コスト・速度・品質のトレードオフを最適化できる。

#### Acceptance Criteria

1. WHEN Context Orchestrator がタスクを受け取る, THE Model Router SHALL タスクの複雑度（分類、要約、推論など）を評価してスコアを算出する
2. WHEN Model Router がタスクの複雑度を評価する, THE Model Router SHALL スコアが閾値以下の軽量タスク（埋め込み生成、スキーマ分類、100トークン以下の要約）をローカルの小型モデルに振り分ける
3. WHEN Model Router がタスクの複雑度を評価する, THE Model Router SHALL スコアが閾値を超える重量タスク（複雑な推論、500トークン以上の要約、調査依頼書生成）をCLI経由でユーザー契約のクラウドLLMに振り分ける
4. WHEN Model Router がCLI経由でクラウドLLMを呼び出す, THE Model Router SHALL 環境変数 `CONTEXT_ORCHESTRATOR_INTERNAL=1` を設定してバックグラウンドでCLI（claude/codex）を起動する
5. WHEN PowerShellラッパー関数が環境変数 `CONTEXT_ORCHESTRATOR_INTERNAL=1` を検出する, THE PowerShell Wrapper SHALL 会話を記録せずに元のCLIコマンドを実行する
6. WHEN CLI経由のクラウドLLM呼び出しが失敗する, THE Model Router SHALL ローカルモデルにフォールバックし、警告をログに記録する

#### 技術実装の詳細

**推奨モデル構成:**

| タスク | 使用モデル | 理由 | コスト | メモリ |
|---|---|---|---|---|
| 埋め込み生成 | ローカル（nomic-embed-text） | 常に必要、軽量、プライバシー重要 | 0円 | 200MB |
| スキーマ分類 | ローカル（Qwen2.5-3B Q4_K_M） | 簡単、プライバシー重要 | 0円 | 2GB |
| 100トークン要約 | ローカル（Qwen2.5-3B Q4_K_M） | 十分な品質 | 0円 | 2GB |
| 500トークン要約 | CLI経由（Claude/GPT） | 高品質が必要 | 0円（既存契約） | 0MB |
| 調査依頼書生成 | CLI経由（Claude/GPT） | 複雑な推論が必要 | 0円（既存契約） | 0MB |
| 記憶の統合 | CLI経由（Claude/GPT） | 複雑な推論が必要 | 0円（既存契約） | 0MB |

**ローカルLLM仕様:**
- **埋め込みモデル**: nomic-embed-text (137M, Q4_K_M)
  - 日本語・英語対応
  - 高品質、軽量
- **推論モデル**: Qwen2.5-3B-Instruct (3B, Q4_K_M)
  - 日本語が非常に強い
  - 英語も対応
  - CPU推論でも実用的な速度
- **実行環境**: Ollama（CPU動作）
- **量子化**: Q4_K_M（4bit量子化）
  - モデルサイズを約1/4に圧縮
  - 精度は実用レベルを維持
  - CPU推論速度が2-3倍向上

**システム要件:**
- 最小: 8GB RAM、4コアCPU（動作はするが遅い）
- 推奨: 16GB RAM、8コアCPU（快適に動作）
- 理想: 32GB RAM、16コアCPU（高速動作）

**メモリ使用量:**
- 常駐: 約1GB（Context Orchestrator + Chroma DB + nomic-embed-text）
- ピーク: 約3GB（Qwen2.5-3B推論時）
- CLI経由クラウドLLM使用時: メモリ増加なし

**バックグラウンドCLI呼び出しの記録防止:**

PowerShellラッパー関数の実装:
```powershell
function claude {
    [CmdletBinding()]
    param([Parameter(ValueFromRemainingArguments=$true)]$args)
    
    # 内部呼び出しチェック
    if ($env:CONTEXT_ORCHESTRATOR_INTERNAL -eq '1') {
        # 記録せずに元のコマンドを実行
        & claude.exe $args
        return
    }
    
    # 通常の呼び出し（記録する）
    $output = & claude.exe $args | Tee-Object -Variable capturedOutput
    
    # バックグラウンドでContext Orchestratorに送信
    Start-Job -ScriptBlock {
        param($output)
        # ... 記録処理 ...
    } -ArgumentList ($capturedOutput -join "`n")
    
    return $output
}
```

Context Orchestrator内部:
```python
import os
import subprocess

def call_claude_background(prompt: str) -> str:
    """バックグラウンドでClaude CLIを呼び出す（記録なし）"""
    env = os.environ.copy()
    env['CONTEXT_ORCHESTRATOR_INTERNAL'] = '1'  # フラグを設定
    
    result = subprocess.run(
        ['claude', prompt],
        capture_output=True,
        text=True,
        env=env,
        timeout=30
    )
    return result.stdout
```

**深夜バッチ処理での活用:**
- 深夜3:00 AMの統合処理でCLI経由クラウドLLMを使用
- 速度のオーバーヘッド（1-2秒/タスク）は許容範囲
- 使用量制限を効率的に活用
- 制限到達時はローカルLLMにフォールバック

### Requirement 11 (MVP) - Context Orchestrator API仕様

**User Story:** 開発者として、任意のMCPクライアント（Claude CLI、Codex CLI、Cursor、Kiroなど）からContext Orchestratorに統一的にアクセスしたい。これにより、ツールを変えても同じ外部脳を使用できる。

#### Acceptance Criteria

1. WHEN Context Orchestrator が起動する, THE Context Orchestrator SHALL stdio（標準入出力）でJSON-RPCメッセージを受信する準備を整える
2. WHEN MCPクライアントがContext Orchestratorを起動する, THE MCP Client SHALL 独自のContext Orchestratorプロセスを起動し、stdinにJSON-RPCリクエストを送信する
3. WHEN 複数のMCPクライアントが同時に動作する, THE System SHALL 各クライアントが独自プロセスを持ち、共有データベース（Chroma DB）にアクセスする
4. WHEN Context Orchestrator がMCPツール `ingest_conversation` を受信する, THE Context Orchestrator SHALL 会話を記録し、スキーマ正規化、チャンク化、索引化を自動的に実行する
5. WHEN Context Orchestrator がMCPツール `search_memory` を受信する, THE Context Orchestrator SHALL ハイブリッド検索を実行し、上位10件の記憶を返す
6. WHEN Context Orchestrator がMCPツール `get_memory` を受信する, THE Context Orchestrator SHALL 指定されたIDの記憶の詳細を返す
7. WHEN Context Orchestrator がMCPツール `list_recent_memories` を受信する, THE Context Orchestrator SHALL 最近の記憶を時系列順に返す
8. WHEN Context Orchestrator がMCPツール `consolidate_memories` を受信する, THE Context Orchestrator SHALL 記憶の統合処理を手動で実行する

#### 技術実装の詳細

**通信方式:**
- stdio（標準入出力）でJSON-RPCメッセージ
- 各MCPクライアントが独自プロセスを起動
- データベース（Chroma DB、BM25索引）は共有

**プロセス構成:**
```
Claude CLI → Context Orchestrator (プロセスA) ┐
                                            ├→ 共有 Chroma DB
Codex CLI → Context Orchestrator (プロセスB) ┘
```

**提供するMCPツール:**

1. **ingest_conversation（自動実行）**
   - 会話を記録
   - バックグラウンドで自動的に呼ばれる

2. **search_memory（自動実行）**
   - 記憶を検索
   - LLMクライアントが質問時に自動的に呼ぶ

3. **get_memory（自動実行）**
   - 特定の記憶を取得
   - 検索結果から詳細を取得する際に自動的に呼ばれる

4. **list_recent_memories（手動実行）**
   - 最近の記憶を一覧表示
   - ユーザーが「最近の記憶を見せて」と指示

5. **consolidate_memories（手動実行）**
   - 記憶の統合を手動実行
   - ユーザーが「記憶を整理して」と指示

**認証:**
- なし（ローカル環境のため不要）
- プロセス間通信なので、外部からアクセスできない
- OSレベルのアクセス制御で十分

**拡張性:**
- 将来的にHTTP/SSE方式を追加可能（Phase 2）
- 外部検索統合時に認証を検討（Future）

### Requirement 12 (MVP) - ストレージ層の仕様

**User Story:** 開発者として、記憶が安全かつ効率的にローカルストレージに保存され、長期的に使用できることを期待する。これにより、システムが安定的に動作する。

#### Acceptance Criteria

1. WHEN Context Orchestrator が初回起動する, THE Context Orchestrator SHALL ユーザーディレクトリ（`~/.context-orchestrator/`）にデータディレクトリを作成する
2. WHEN 記憶を保存する, THE Context Orchestrator SHALL Chroma DB（SQLiteベース）にベクトルと構造化データを保存する
3. WHEN 記憶を保存する, THE Context Orchestrator SHALL BM25索引（Pythonライブラリ）にキーワード索引を保存する
4. WHEN ディスク使用量を計算する, THE System SHALL 1年で約10MB、10年で約100MBのディスク容量を使用する
5. WHEN ユーザーがエクスポートを実行する, THE Context Orchestrator SHALL 全ての記憶をJSON形式でエクスポートする
6. WHEN ユーザーがインポートを実行する, THE Context Orchestrator SHALL JSONファイルから記憶を復元する

#### 技術実装の詳細

**ファイル構造:**
```
C:\Users\{username}\.context-orchestrator\
├── config.yaml              # 設定ファイル
├── chroma_db\               # ベクトルDB（記憶を全て保存）
│   └── chroma.sqlite3       # SQLiteデータベース
├── bm25_index\              # BM25索引
│   └── index.pkl            # Pickle形式の索引
└── logs\                    # ログファイル
    └── orchestrator.log
```

**ベクトルDB:**
- **Chroma**（SQLiteベース）
- シンプル、セットアップ不要
- ローカルファイルに保存
- 個人利用（数万件の記憶）に最適

**データ永続化:**
- ベクトルDBのみ（JSONファイルは作らない）
- エクスポート機能で手動バックアップ可能
- 元データ（CLI会話ログ、Obsidianノート）から再構築可能

**ディスク使用量:**
- 1つの記憶: 約2KB（ベクトル + メタデータ）
- 1日10件 × 365日 = 3,650件/年
- 3,650件 × 2KB = 約7.3MB/年
- 10年: 約73MB（Chroma DB）
- BM25索引: 約10MB
- **合計: 約100MB（10年分）**

**バックアップ:**
- デフォルトはオフ
- オプション機能として提供
- 重要な記憶のみバックアップ可能（Phase 2）

**復元方法:**
1. エクスポートファイルからインポート
2. 元データ（CLI会話ログ、Obsidianノート）から再構築

**エクスポート/インポートコマンド:**
```powershell
# エクスポート
context-orchestrator export --output memories_backup.json

# インポート
context-orchestrator import --input memories_backup.json
```

### Requirement 13 (MVP) - セットアップと運用

**User Story:** 新規ユーザーとして、システムを簡単にセットアップし、すぐに使い始めたい。これにより、導入の障壁が低くなる。

#### Acceptance Criteria

1. WHEN 新規ユーザーがシステムをインストールする, THE System SHALL pip 配布チャネルが利用可能な場合に pip install context-orchestrator を案内し、利用できない場合は README とセットアップスクリプトでローカル手順を提示する
2. WHEN 新規ユーザーがセットアップを実行する, THE System SHALL 対話的なセットアップウィザードを提供する
3. WHEN セットアップウィザードが起動する, THE System SHALL Ollamaのインストール状態を確認し、必要に応じてインストール手順を提示する
4. WHEN セットアップウィザードがOllamaを確認する, THE System SHALL 推奨モデル（nomic-embed-text、qwen2.5:7b）を自動的にダウンロードする
5. WHEN セットアップウィザードがObsidian Vaultパスを要求する, THE System SHALL ユーザーにパスを入力させ、Vaultの存在を確認する
6. WHEN セットアップウィザードがPowerShellプロファイル設定を要求する, THE System SHALL ユーザーの承認を得てPowerShellプロファイルにラッパー関数を追加する
7. WHEN セットアップが完了する, THE System SHALL 動作確認コマンドとサンプルクエリを提示する
8. WHEN ユーザーがヘルスチェックを実行する, THE System SHALL `context-orchestrator status` でシステムの状態を表示する
9. WHEN ユーザーがトラブルシューティングを実行する, THE System SHALL `context-orchestrator doctor` で問題を診断し、修復方法を提示する

#### 技術実装の詳細

**インストール方法:**
`powershell
# pip 配布チャネルが利用可能な場合
pip install context-orchestrator

# ローカル環境での標準セットアップ
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
`
# Pythonパッケージとしてインストール
1. WHEN 新規ユーザーがシステムをインストールする, THE System SHALL pip 配布チャネルが利用可能な場合に pip install context-orchestrator を案内し、利用できない場合は README とセットアップスクリプトでローカル手順を提示する
```

**セットアップの流れ:**
```powershell
> context-orchestrator setup

Welcome to Context Orchestrator Setup!

[1/6] Checking Ollama installation...
✓ Ollama is running

[2/6] Installing required models...
Downloading nomic-embed-text... ✓
Downloading qwen2.5:7b... ✓

[3/6] Obsidian Vault path:
Enter path (or press Enter to skip): C:\Users\username\Documents\MyVault
✓ Vault found

[4/6] Cloud LLM API keys (optional):
Enter Anthropic API key (or press Enter to skip): 
Skipped.

[5/6] PowerShell profile setup:
Add CLI recording wrapper? (y/n): y
✓ Added to PowerShell profile

[6/6] Batch processing schedule:
Daily consolidation time (default: 03:00): 
✓ Set to 03:00

Setup complete! 🎉

Next steps:
1. Restart PowerShell
2. Try: claude "test message"
3. Check: context-orchestrator status
```

**依存関係:**
- **Python 3.11+**（ユーザーが事前インストール）
- **Ollama**（セットアップスクリプトが自動インストール）
- **Claude/Codex CLI**（ユーザーが事前インストール）

**ヘルスチェック:**
```powershell
> context-orchestrator status

Context Orchestrator Status:
✓ Ollama: Running
✓ Models: nomic-embed-text, qwen2.5:7b
✓ Database: 0 memories
✓ Obsidian Vault: Connected (C:\Users\...\MyVault)
✓ PowerShell wrapper: Active
```

**トラブルシューティング:**
```powershell
> context-orchestrator doctor

Checking Ollama...
✗ Ollama is not running

Fix:
1. Start Ollama: ollama serve
2. Or install: winget install Ollama.Ollama

Checking PowerShell wrapper...
✗ Wrapper function not found in profile

Fix:
1. Re-run setup: context-orchestrator setup --repair
2. Or manually add to profile: notepad $PROFILE

Checking CLI recording...
✗ No recent recordings

Fix:
1. Check wrapper: Get-Command claude
2. Check logs: context-orchestrator logs
3. Test manually: context-orchestrator ingest --test
```

**動作確認:**
```powershell
# テスト記録
> claude "test message"
Hello! This is a test.

# 記憶確認
> context-orchestrator list-recent
1. [2025-01-15 10:30] User: test message
   Assistant: Hello! This is a test.
```

**補足（配布方針）:**
- pip install context-orchestrator は将来の拡張オプションとして維持し、MVP 時点ではリポジトリ配布とセットアップスクリプトを標準とする

---

## Phase 2 Requirements

以下の要件は、MVPの安定稼働後に実装する拡張機能である。

### Requirement 21 (Phase 2) - 記憶の階層的圧縮

**User Story:** 開発者として、時間経過に応じて記憶を階層的に圧縮し、詳細→要約→エッセンスと段階的に情報量を減らしたい。これにより、ストレージ効率が向上する。

#### Acceptance Criteria

1. WHEN 記憶が7日経過する, THE Context Orchestrator SHALL Level 0（生データ）からLevel 1（要約）に圧縮する
2. WHEN 記憶が30日経過する, THE Context Orchestrator SHALL Level 1（要約）からLevel 2（エッセンス）に圧縮する
3. WHEN 記憶が90日経過する, THE Context Orchestrator SHALL Level 2（エッセンス）をLevel 3（アーカイブ）に移動し、生データを圧縮保存する
4. WHEN 圧縮された記憶を参照する, THE Context Orchestrator SHALL 必要に応じてアーカイブから復元する
5. WHEN 記憶の重要度が高い, THE Context Orchestrator SHALL 圧縮をスキップし、生データを保持する

### Requirement 22 (Phase 2) - 重要度ベースの保持

**User Story:** 開発者として、記憶の重要度を自動的に評価し、重要な記憶を優先的に保持したい。これにより、価値の高い記憶が失われない。

#### Acceptance Criteria

1. WHEN Context Orchestrator が記憶の重要度を評価する, THE Context Orchestrator SHALL 参照頻度、最近性、中心性、成功体験、ユニーク性を考慮してスコアを算出する
2. WHEN 重要度スコアが高い, THE Context Orchestrator SHALL 記憶を長期記憶に昇格させる
3. WHEN 重要度スコアが低い, THE Context Orchestrator SHALL 記憶を削除候補としてマークする
4. WHEN 開発者が記憶を明示的に保存する, THE Context Orchestrator SHALL 重要度スコアを最大値に設定する
5. WHEN 記憶が成功体験である, THE Context Orchestrator SHALL 重要度スコアを2倍にする

### Requirement 23 (Phase 2) - 自発的な想起（Proactive Recall）

**User Story:** 開発者として、現在の作業に関連する過去の記憶を自動的に思い出してほしい。これにより、過去の経験を活かせる。

#### Acceptance Criteria

1. WHEN 開発者が新しいタスクを開始する, THE Context Orchestrator SHALL 類似した過去のタスクを自動的に検索する
2. WHEN 関連する記憶を発見する, THE Context Orchestrator SHALL 「以前こんなことがありました」と提示する
3. WHEN エラーが発生する, THE Context Orchestrator SHALL 同じエラーの過去の解決策を自動的に提示する
4. WHEN 新しい技術を使う, THE Context Orchestrator SHALL 過去の学習メモや関連するSnippetを自動的に表示する
5. WHEN 間隔反復学習の復習タイミングである, THE Context Orchestrator SHALL 「そろそろ復習しませんか？」と提案する

### Requirement 24 (Phase 2) - 記憶の関連付け（Memory Graph）

**User Story:** 開発者として、記憶同士の関連性を自動的に発見し、知識グラフを構築したい。これにより、記憶のネットワークが形成される。

#### Acceptance Criteria

1. WHEN 新しい記憶を保存する, THE Context Orchestrator SHALL 既存の記憶との関連性（因果関係、時系列、共起）を分析する
2. WHEN 因果関係を検出する, THE Context Orchestrator SHALL 「AがBの原因」という関係をMemory Graphに記録する
3. WHEN 時系列の関連を検出する, THE Context Orchestrator SHALL 「Aの後にBが起きた」という関係をMemory Graphに記録する
4. WHEN 記憶を検索する, THE Context Orchestrator SHALL 関連する記憶をグラフとして可視化する
5. WHEN 記憶の中心性が高い, THE Context Orchestrator SHALL 重要度スコアを増加させる

### Requirement 25 (Phase 2) - 文脈の連続性（Context Continuity）

**User Story:** 開発者として、過去の会話や作業の文脈を常に保持し、「前回の続き」ができるようにしたい。これにより、シームレスな作業が可能になる。

#### Acceptance Criteria

1. WHEN 開発者が作業を再開する, THE Context Orchestrator SHALL 前回の文脈（最後に参照したファイル、実行したコマンド、議論した内容）を自動的に復元する
2. WHEN 開発者が「あれ」「それ」と言う, THE Context Orchestrator SHALL 文脈から参照先を特定する
3. WHEN 長期間経過する, THE Context Orchestrator SHALL 文脈の要約を保持して詳細は圧縮する
4. WHEN 複数のプロジェクトを切り替える, THE Context Orchestrator SHALL プロジェクトごとの文脈を分離して管理する
5. WHEN 文脈が失われる, THE Context Orchestrator SHALL 「前回の続きを復元できませんでした」と通知し、手動復元を提案する

### Requirement 26 (Phase 2) - セッションログと自動要約 (Session Logging & Summaries)

**User Story:** 開発者として、各ターミナル／LLMセッションの対話ログを保持し、終了時に自動要約したい。これにより、トークン上限やリセットが発生しても作業履歴を失わず、次回起動時に文脈を引き継げる。（As a developer, I want each terminal or LLM session to retain its transcript and auto-summarize at shutdown so that context resets do not erase my work.）

#### Acceptance Criteria

1. WHEN 新しいターミナルウィンドウまたは MCP クライアント接続が開始されたなら、THE Context Orchestrator SHALL 一意の session_id を発行し、stdin/stdout/stderr を logs/<session_id>.log にストリーム保存する。
2. WHEN セッショントランスクリプトを記録するとき、THE Context Orchestrator SHALL セッション単位でログファイルを分離し、ターミナルAとBの履歴が混在しないようにする。
3. WHEN セッションが正常終了またはトークン／コンテキスト上限で中断されたなら、THE Context Orchestrator SHALL 収集したログをローカルLLMの要約ジョブへ渡し、session_id・開始/終了時刻・使用モデル付きで知識ベースに保存する。
4. WHEN 要約ジョブが失敗したなら、THE Context Orchestrator SHALL 元のログを保持し、リトライタスクをキューに登録するとともにユーザーへ対処方法を通知する。
5. WHEN ユーザーが特定セッションの履歴を要求したなら、THE Context Orchestrator SHALL session_id ごとに生ログと生成済み要約を返す。
6. WHEN ログファイルが設定サイズ（例: 10MB）を超えたなら、THE Context Orchestrator SHALL ファイルをローテーションし、アクティブセグメントの監視と要約を継続する。

---

## Future Requirements (Optional)

以下の要件は、将来的に検討する拡張機能である。

### 構造化調査依頼書生成（外部検索統合）

**User Story:** 開発者として、内部記憶が不足している場合、外部調査用の構造化された依頼書を自動生成したい。

#### Acceptance Criteria

1. WHEN 内部検索の信頼度が閾値以下である, THE Context Orchestrator SHALL 不足している情報を特定する
2. WHEN 不足情報を特定する, THE Context Orchestrator SHALL Deep Research用の構造化調査依頼書を生成する
3. WHEN 調査依頼書を生成する, THE Context Orchestrator SHALL 調査目的、背景、調査項目、期待成果物を含める
4. WHEN 外部調査結果を受け取る, THE Context Orchestrator SHALL PDF保存、テキスト抽出、要約統合を実行する
5. WHEN 外部調査結果を統合する, THE Context Orchestrator SHALL 「source: external」「verified: false」のメタデータを付与する

### 新規ユーザーオンボーディング

**User Story:** 新規ユーザーとして、GitHubからシステムをクローンし、最小限の設定で動作させたい。

#### Acceptance Criteria

1. WHEN 新規ユーザーがリポジトリをクローンする, THE System SHALL README.mdに明確なセットアップ手順を提供する
2. WHEN 新規ユーザーが初回セットアップを実行する, THE System SHALL 依存関係を自動的にインストールするスクリプトを提供する
3. WHEN 新規ユーザーが設定ファイルを作成する, THE System SHALL デフォルト設定のテンプレートとサンプルを提供する
4. WHEN 新規ユーザーがローカルLLMをセットアップする, THE System SHALL 推奨モデルのダウンロードとインストール手順を提供する
5. WHEN 新規ユーザーが動作確認を実行する, THE System SHALL ヘルスチェックコマンドとサンプルクエリを提供する

### ライセンスと利用条件

**User Story:** ユーザーとして、システムのライセンスと利用条件を明確に理解したい。

#### Acceptance Criteria

1. WHEN ユーザーがリポジトリを確認する, THE System SHALL LICENSEファイルにオープンソースライセンス（MIT、Apache 2.0など）を明記する
2. WHEN ユーザーがサードパーティライブラリを確認する, THE System SHALL 依存ライブラリのライセンス情報を一覧化する
3. WHEN ユーザーがローカルLLMモデルを使用する, THE System SHALL モデルのライセンスと利用条件を明記する
