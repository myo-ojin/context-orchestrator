# Context Orchestrator - 機能解説（日本語）

## 📚 このシステムでできること

Context Orchestratorは**開発者の外部脳**として、あなたの開発経験を自動的に記録・整理・検索できるMCPサーバーです。

---

## 🎯 主要機能

### 1️⃣ 会話の自動記録
**何ができる？**
- Claude CLI、Cursor、VS Code等でのLLM会話を自動保存
- PowerShell/ターミナルでのコマンド実行履歴を記録
- Obsidianのメモから会話を自動検出・取り込み

**使用例**：
```bash
# PowerShellでClaudeを使う
claude "Pythonのエラーを修正して"
# → 会話が自動的にContext Orchestratorに保存される

# Obsidianでメモを作成
# → **User:** / **Assistant:** 形式の会話を自動検出して取り込み
```

**どう便利？**
- 手動でメモを取る必要なし
- あとから「あのとき何を聞いたっけ？」を検索できる
- 会話履歴が消えても安心（ローカルに永続保存）

---

### 2️⃣ 知識の自動分類
**何ができる？**
会話を4つのカテゴリに自動分類：

| カテゴリ | 内容 | 具体例 |
|---------|------|--------|
| **Incident** | バグ・エラー・修正 | 「TypeErrorが出た」「原因はnull参照」 |
| **Snippet** | コード片・使用例 | 「Reactのカスタムフック実装」 |
| **Decision** | 設計判断・選択 | 「REST vs GraphQL、RESTを選んだ理由」 |
| **Process** | 試行錯誤・学習 | 「パフォーマンス改善の試行プロセス」 |

**どう便利？**
- 「バグの解決法だけ検索」が可能
- 「設計判断の履歴」を後から振り返れる
- 「よく使うコード片」をすぐ見つけられる

---

### 3️⃣ ハイブリッド検索
**何ができる？**
2種類の検索を組み合わせて精度向上：

- **ベクトル検索**：意味が似た内容を検索（「認証エラー」→「ログイン失敗」も見つかる）
- **キーワード検索**：完全一致で検索（「TypeError」→正確にヒット）

**使用例**：
```python
# MCP経由で検索（Claude Desktop、Cursorから）
results = search_memory("React hooksのエラー処理")

# CLI経由で検索
python -m src.cli search "React hooksのエラー処理"
```

**検索結果**：
- 関連度の高い順にランキング
- 元の会話へのリンク（GitHub PR、ファイルパス等）
- 関連する他のメモリも表示

**どう便利？**
- 曖昧な記憶でも見つかる（「あのReactのやつ」で検索できる）
- 過去の解決策を数秒で発見
- 同じ問題を何度も調べ直す時間を削減

---

### 4️⃣ メモリの階層管理
**何ができる？**
人間の脳のように、記憶を3段階で管理：

```
作業記憶（数時間）
  ↓ 自動移行
短期記憶（数日〜数週間）
  ↓ 重要度判定
長期記憶（永続的）
```

**自動処理**：
- 毎晩3:00に記憶の整理実行（consolidation）
- 似た記憶をまとめる（クラスタリング）
- 古くて重要度が低い記憶を削除（forgetting）

**どう便利？**
- 重要な知識は残り、ノイズは消える
- ディスク容量を圧迫しない（年間10MB程度）
- 検索速度が劣化しない

---

### 5️⃣ セッション履歴の保存
**何ができる？**
- ターミナルでの全てのやり取りを保存
- セッション終了時に自動要約
- 過去のセッションをいつでも参照可能

**使用例**：
```bash
# セッション一覧
python -m src.cli session-history

# 特定のセッションを表示
python -m src.cli session-history --session-id abc123

# 要約だけ表示
python -m src.cli session-history --session-id abc123 --summary-only

# エディタで開く
python -m src.cli session-history --session-id abc123 --open
```

**どう便利？**
- 「先週やった作業」を詳細に振り返れる
- トークン制限で消えた会話も残る
- チームメンバーに作業内容を共有しやすい

---

### 6️⃣ Obsidian連携
**何ができる？**
- Obsidianのマークダウンファイルを監視
- `**User:**` / `**Assistant:**` 形式の会話を自動検出
- Wikilink（`[[リンク]]`）の関係性も記録

**設定**：
```yaml
# ~/.context-orchestrator/config.yaml
obsidian_vault_path: C:\Users\username\Documents\ObsidianVault
```

**どう便利？**
- 既存のObsidian知識ベースと統合
- 手動メモも自動的に検索可能に
- Obsidianで整理、Context Orchestratorで検索

---

### 7️⃣ プライバシー重視の設計
**何ができる？**
- **全データをローカル保存**（`~/.context-orchestrator/`）
- 埋め込み生成は**常にローカルLLM**（Ollama）
- クラウドLLMは複雑な処理のみ（ユーザー選択可能）

**データフロー**：
```
[会話入力]
  ↓
[ローカルLLMで分類・埋め込み生成] ← プライバシー保護
  ↓
[ローカルDBに保存] ← 外部送信なし
  ↓
[必要に応じてクラウドLLMで要約] ← オプション
```

**どう便利？**
- 機密情報が外部に漏れない
- インターネット不要で検索可能
- API利用料を最小化（埋め込みは無料）

---

## 🔧 具体的な使い方

### パターン1: Claude CLIと連携
```bash
# 1. Context Orchestratorを起動（バックグラウンド）
python -m src.main &

# 2. 普段通りClaude CLIを使う
claude "Reactのカスタムフックを実装したい"
# → 自動的に記録される

# 3. 後から検索
python -m src.cli search "React カスタムフック"
```

### パターン2: MCP経由で利用（Claude Desktop/Cursor）
```json
// Claude Desktop設定
{
  "mcpServers": {
    "context-orchestrator": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "/path/to/llm-brain"
    }
  }
}
```

Claude Desktopから：
```
User: 過去にReactのエラー処理について話したことある？
Claude: [Context Orchestratorで検索...]
        はい、3ヶ月前にuseEffectのクリーンアップについて話しました。
```

### パターン3: Obsidianと連携
```markdown
<!-- Obsidian: daily-note.md -->
## 今日の作業メモ

**User:** Pythonの型ヒントでGenericsを使うには？

**Assistant:** Genericsを使うには`typing.Generic`をインポート...

[[関連ページ]]
```
↓ **自動検出・取り込み**
```bash
python -m src.cli search "Python Generics"
# → Obsidianのメモも検索結果に含まれる
```

---

## 📊 システムステータス確認

```bash
# 総合ステータス
python -m src.cli status

# 出力例:
# ✓ Ollama: Connected (http://localhost:11434)
# ✓ Vector DB: 1,234 memories indexed
# ✓ BM25 Index: Ready
# ✓ Last Consolidation: 2025-01-15 03:00:00
# ✓ Session Logs: 45 sessions
```

---

## 🎯 ユースケース

### 1. バグの再発防止
```bash
# 過去のバグ解決法を検索
python -m src.cli search "TypeError null参照" --schema Incident

# 結果: 3ヶ月前に同じバグを解決済み
# → 修正方法を即座に再利用
```

### 2. コードレビューで過去の判断を参照
```bash
# 設計判断の履歴を検索
python -m src.cli search "REST API 設計 理由" --schema Decision

# 結果: GraphQLではなくRESTを選んだ理由を確認
# → 一貫した設計判断が可能
```

### 3. 新メンバーのオンボーディング
```bash
# プロジェクトの全記憶をエクスポート
python -m src.cli export --output project-knowledge.json

# 新メンバーの環境にインポート
python -m src.cli import --input project-knowledge.json

# → チームの知識を即座に共有
```

### 4. 週次レポート作成
```bash
# 今週のセッション一覧
python -m src.cli session-history --from 2025-01-08

# 各セッションの要約を確認
python -m src.cli session-history --session-id xxx --summary-only

# → 作業報告書をすぐ作成
```

---

## ⚡ パフォーマンス

- **検索速度**: 80-200ms（10,000件の記憶でも高速）
- **メモリ使用量**: 約1GB（ピーク時3GB）
- **ディスク使用量**: 年間10MB程度
- **取り込み時間**: 1会話あたり5秒以下

```bash
# パフォーマンス測定
python scripts/performance_profiler.py

# レポート出力:
# - P50/P95/P99レイテンシ
# - スループット
# - メモリフットプリント
```

---

## 🔒 セキュリティ

- **ローカル保存**: `~/.context-orchestrator/`にすべて保存
- **暗号化**: OSのファイルシステム権限で保護
- **外部送信なし**: 埋め込み生成・検索は完全にローカル
- **オプトイン**: クラウドLLMの使用は設定で制御可能

---

## 🚀 次のステップ

1. **セットアップ**:
   ```bash
   python scripts/setup.py
   ```

2. **動作確認**:
   ```bash
   python -m src.cli doctor
   ```

3. **試しに使う**:
   ```bash
   # テスト会話を取り込み
   python -m src.main
   # → MCP経由で会話を送信

   # 検索してみる
   python -m src.cli search "テスト"
   ```

4. **本格運用**:
   - Claude CLI/Desktop/Cursorと連携
   - Obsidianと統合
   - 毎晩の自動統合を設定

---

## 📚 関連ドキュメント

- [README.md](README.md) - プロジェクト概要
- [CLAUDE.md](CLAUDE.md) - 開発者ガイド
- [TESTING_ON_GITHUB.md](TESTING_ON_GITHUB.md) - テスト実行方法
- [INTEGRATION_TEST_RESULTS.md](INTEGRATION_TEST_RESULTS.md) - テスト結果

---

## ❓ よくある質問

**Q: Claude Desktop以外でも使える？**
A: はい。MCP対応のすべてのクライアント（Cursor、VS Code拡張等）で利用可能です。

**Q: データはどこに保存される？**
A: `~/.context-orchestrator/`にすべてローカル保存されます。外部サーバーには一切送信されません。

**Q: 有料のAPIキーは必要？**
A: 基本機能（埋め込み・検索）はOllama（無料）で動作します。複雑な要約にのみクラウドLLM（オプション）を使用します。

**Q: 既存のメモをインポートできる？**
A: はい。Obsidian連携または`import`コマンドでJSON形式のメモをインポート可能です。

**Q: チームで共有できる？**
A: `export/import`コマンドでJSON形式でエクスポート・共有可能です。各メンバーがローカルで運用します。

---

**Context Orchestrator = あなたの開発経験を記録・検索・活用する外部脳** 🧠✨
