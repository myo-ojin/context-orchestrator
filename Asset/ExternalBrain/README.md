# External Brain Runtime

## 概要

External Brain は、LLM エージェントが過去の判断・トラブルシュート・パターンを構造化して蓄積・検索・活用するためのナレッジシステム。

**なぜ作ったか**: Claude Code のエージェントは毎回ゼロからコンテキストを構築する。同じ問題に何度も遭遇しても、過去の解決策を自動的に参照する仕組みがない。External Brain は「経験の蓄積」を仕組みで保証し、エージェントの判断品質を反復的に向上させる。

## アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│  Claude Code Agent                              │
│  (build-error-resolver / security-reviewer /    │
│   code-reviewer / tdd-guide)                    │
└──────────┬──────────────────────────────────────┘
           │ python3 playbook_api.py <command>
           ▼
┌─────────────────────────────────────────────────┐
│  playbook_api.py (Composer Layer)               │
│  ┌──────────┐ ┌────────┐ ┌──────────────────┐  │
│  │ TF-IDF   │ │ EWA    │ │ Event Logger     │  │
│  │ Search   │ │ Conf.  │ │ (events.jsonl)   │  │
│  └──────────┘ └────────┘ └──────────────────┘  │
│  ┌──────────────┐ ┌────────────────────────┐   │
│  │ Time Decay   │ │ Working Memory         │   │
│  │ (lazy eval)  │ │ (ephemeral KV store)   │   │
│  └──────────────┘ └────────────────────────┘   │
└──────────┬──────────────────────────────────────┘
           │ read / write Markdown + YAML frontmatter
           ▼
┌─────────────────────────────────────────────────┐
│  Vault (ExternalBrain/)                         │
│  ├── Playbooks/       19 件の知識カード         │
│  ├── Inbox/           未昇格の候補              │
│  ├── WorkingMemory/   作業記憶 (TTL付きKV)      │
│  └── logs/            events.jsonl              │
└─────────────────────────────────────────────────┘
```

### データフロー

1. **Search** — エージェントがキーワードで検索 → TF-IDF スコアリング → 結果に時間減衰を適用して上位 N 件を返す
2. **Get** — Playbook 本文を取得 → `last_referenced` を更新 → `referenced` イベントをログ
3. **Record** — 使用結果 (`used` / `rejected`) を記録 → EWA で confidence を更新
4. **Create** — 新しい Playbook を作成（型・ドメイン・タグ付き）
5. **Promote** — Inbox の候補を正式な Playbook に昇格
6. **Audit** — ドメイン別カバレッジ + stale playbook 検出 + Working Memory 状態
7. **Remember/Recall/Forget/Context** — 作業記憶の CRUD（TTL 付き短期記憶）

## API リファレンス

### CLI 呼び出し

```bash
BRAIN="runtime/playbook_api.py"

# 検索 (TF-IDF)
python3 "$BRAIN" search "ECS timeout" --domain infra

# 取得 (自動で referenced ログ記録)
python3 "$BRAIN" get "Playbooks/Troubleshooting_ECS_External_API_Timeout_via_SG_Egress.md"

# 使用記録 (confidence 更新)
python3 "$BRAIN" record "Playbooks/..." used "SG egress 修正で解決"
python3 "$BRAIN" record "Playbooks/..." rejected "状況が異なった"

# 新規作成
python3 "$BRAIN" create \
  --type troubleshooting \
  --domain infra \
  --tags "ecs,timeout,sg" \
  --title "ECS External API Timeout via SG Egress" \
  --body "# Title\n\n## Symptoms\n..."

# Inbox → Playbook 昇格
python3 "$BRAIN" promote "Inbox/candidate.md" \
  --type pattern --domain dev --title "New Pattern"

# 監査レポート
python3 "$BRAIN" audit

# 作業記憶 (Working Memory)
python3 "$BRAIN" remember "current-task" --body "ECS deploy 作業中" --ttl 7
python3 "$BRAIN" recall "current-task"
python3 "$BRAIN" context
python3 "$BRAIN" forget "current-task"
```

### コマンド一覧

| コマンド | 説明 | ログ記録 | confidence 更新 |
|----------|------|----------|-----------------|
| `search` | TF-IDF でキーワード検索 | なし | 時間減衰を適用 |
| `get` | Playbook 本文取得 | `referenced` | `last_referenced` 更新 |
| `record` | 使用/棄却の記録 | `used` / `rejected` | EWA で更新 |
| `create` | 新規 Playbook 作成 | `created` | 初期値 0.5 |
| `promote` | Inbox → Playbook 昇格 | `promoted` | 初期値 0.5 |
| `audit` | カバレッジ監査 + stale 検出 | なし | なし |
| `list` | Playbook 一覧表示 | なし | なし |
| `learn` | 構造化 Inbox 候補作成 | `learned` | なし |
| `remember` | 作業記憶の保存 | `remembered` | なし |
| `recall` | 作業記憶の取得 | なし | なし |
| `forget` | 作業記憶の削除 | `forgotten` | なし |
| `context` | 作業記憶一覧 (期限切れ自動削除) | なし | なし |

## フォルダ構成

```
ExternalBrain/
├── README.md            # この文書
├── Playbooks/           # 正式な知識カード (Markdown + YAML frontmatter)
├── Inbox/               # 未昇格の候補 (search miss / learn で自動生成)
├── WorkingMemory/       # 作業記憶 (TTL 付き一時 KV ストア)
├── logs/                # events.jsonl (全イベントの追記ログ)
└── runtime/             # Python 実装
    ├── playbook_api.py            # メイン API (~1050 行, stdlib のみ)
    ├── auto_learn.py              # 自動学習 (セッション transcript 解析)
    └── tests/
        ├── test_playbook_api.py   # ユニットテスト (91 件)
        ├── test_auto_learn.py     # auto_learn テスト (7 件)
        └── simulation/            # 探索テスト
            ├── seed_vault.py      # テスト用 vault 生成
            ├── sim_driver.py      # シミュレーション実行
            ├── sim_scenarios.py   # シナリオ定義
            └── sim_analysis.py    # 結果分析
```

## エージェント統合

4 つの Claude Code エージェントが External Brain を統合済み:

| エージェント | 用途 | Brain の使い方 |
|-------------|------|---------------|
| `build-error-resolver` | ビルドエラー修正 | エラーパターンを検索 → 既知の解決策を適用 |
| `security-reviewer` | セキュリティレビュー | 脆弱性パターンを検索 → 既知の対策を適用 |
| `code-reviewer` | コードレビュー | 既知のアンチパターンを検索 → レビューに反映 |
| `tdd-guide` | テスト駆動開発 | テストパターンを検索 → テスト設計に反映 |

### エージェントの Brain 使用プロトコル

1. 作業開始前に `search` で関連 Playbook を探す
2. ヒットしたら `get` で本文を取得（自動ログ）
3. 適用したら `record ... used`、不適切なら `record ... rejected`
4. 新パターン発見時は `create` で蓄積

### Confidence に基づくアクション

| Confidence | アクション |
|-----------|-----------|
| >= 0.8 | 高確信で適用 |
| 0.5 - 0.79 | 適用するが検証も行う |
| < 0.5 | 参考情報として扱い、手動確認を推奨 |

## Playbook 一覧 (19 件)

### Troubleshooting (4 件)
- **ECS_External_API_Timeout_via_SG_Egress** — SG egress 不足で外部 API タイムアウト
- **Expo_Fabric_Crash_react_native_screens_Pin** — react-native-screens Fabric クラッシュ
- **GitHub_PAT_Org_Webhook_404_Error** — Org 未承認 PAT で webhook 404
- **Terraform_SG_Rule_Rename_Duplicate_Error** — SG ルール名変更で Duplicate エラー

### Decision Record (4 件)
- **OpenClaw_Tailscale_Remote_Access** — Tailscale リモートアクセス判断
- **Akkadian_Ground_Truth_Format_Sentences_Oare** — Akkadian コンペ GT フォーマット
- **CloudFront_ALB_HTTP_Only_Protocol** — CloudFront → ALB プロトコル選択
- **ECS_Sidecar_Architecture_Backend_Frontend** — ECS サイドカー構成判断

### Runbook (3 件)
- **ECR_Push_from_WSL2** — WSL2 から ECR へ push する手順
- **Secrets_Manager_ECS_Task_Definition_Sync** — Secrets Manager ↔ ECS タスク定義同期
- **Terraform_SSO_Auth_for_CLI** — Terraform SSO 認証手順

### Pattern (5 件)
- **GEO_Audit_Batch_Process_CSV** — GEO audit CSV バッチ処理パターン
- **Next_js_Standalone_Static_Files_via_ALB** — Next.js standalone 静的ファイル配信
- **Pytest_Fixture_Isolation_Pattern** — pytest フィクスチャ分離パターン
- **SQL_Injection_Prevention** — SQL インジェクション防止パターン
- **SSRF_Detection_Pattern** — SSRF 検出パターン

### Checklist (2 件)
- **ECS_Full_Deploy_Checklist** — ECS フルデプロイチェックリスト
- **SSRF_Review_Checklist** — SSRF レビューチェックリスト

### Worker (1 件)
- **Decision_Record_Worker_ECS_BullMQ_Architecture** — Worker ECS BullMQ 構成判断

## Confidence システム

### EWA (Exponential Weighted Average)

Confidence は `record used/rejected` で EWA 更新される。

```
α = 0.1 (smoothing factor)

record "used"     → signal = 1.0
record "rejected" → signal = 0.0

new_conf = α × signal + (1 - α) × old_conf
```

- 初期値: 0.5
- 範囲: [0.0, 1.0]
- `used` を記録するたびに上昇、`rejected` で下降
- 直近のフィードバックに重みを置きつつ、急激な変動を抑制

### 時間減衰 (Time Decay)

長期間参照されない Playbook の confidence を自動的に下げる lazy evaluation 方式。

```
DECAY_THRESHOLD_DAYS = 90    # 90日間参照なしで減衰開始
DECAY_RATE_PER_MONTH = 0.05  # 月あたり -0.05
MIN_CONFIDENCE_FLOOR = 0.1   # 減衰の下限

decayed = max(0.1, conf - 0.05 × months_over_threshold)
```

- `get()` 呼び出し時に `last_referenced` が自動更新される
- `search()` 結果に減衰後 confidence が反映される
- `audit` で stale playbook (90日超) の一覧が表示される
- バックグラウンドプロセス不要（アクセス時に計算）

## Working Memory (作業記憶)

セッションを跨いで「今何をしているか」の文脈を保持する短期記憶層。
Playbook（確定知識）と異なり、一時的・揮発性の KV ストア。

```bash
# 記憶 (default TTL: 7日)
brain remember "current-task" --body "ECS deploy 作業中" --ttl 7

# 想起
brain recall "current-task"

# 一覧 (期限切れは自動削除)
brain context

# 削除
brain forget "current-task"
```

- ファイル形式: `WorkingMemory/<key>.md` (Markdown + frontmatter)
- TTL: デフォルト 7 日。`context` 実行時に自動 purge
- `recall` 時にも TTL チェック — 期限切れは自動削除される

## 既知の制約

1. **TF-IDF の限界** — セマンティック検索ではない。同義語やニュアンスの違いを捉えられない
2. **スケール天井** — Playbook 数が数百件を超えると TF-IDF の精度が低下する可能性
3. **低スコアヒット問題** — 関連性の低い結果も返ることがある（閾値チューニングが必要）
4. **stdlib のみ** — 外部依存なしの設計上、高度な NLP 手法（ベクトル検索等）は未実装
5. **単一ファイルロック** — fcntl ベースのファイルロックで並行書き込みを制御（高頻度アクセスには未対応）

## テスト

### ユニットテスト (98 件)

```bash
cd runtime/
/tmp/brain-venv/bin/python -m pytest tests/ -v
```

### 探索テスト (simulation)

```bash
cd runtime/tests/simulation/
python sim_driver.py    # シミュレーション実行
python sim_analysis.py  # 結果分析
```

### テストカバレッジの主要領域

- CRUD 操作 (create / get / record / promote)
- 検索 (TF-IDF スコアリング、ドメインフィルタ)
- Confidence 更新 (EWA 計算 + 時間減衰)
- Working Memory (remember / recall / forget / context / TTL)
- 自動学習 (parse_transcript / detect_patterns)
- Learn (構造化 Inbox 候補作成)
- Inbox 自動生成 (search miss 時)
- Audit レポート生成 (stale 検出含む)
- エラーハンドリング (不正入力、ファイル不在、TTL 超過)
- ファイルロック (並行書き込み制御)

## 既知の制約

1. **TF-IDF の限界** — セマンティック検索ではない。同義語やニュアンスの違いを捉えられない
2. **スケール天井** — Playbook 数が数百件を超えると TF-IDF の精度が低下する可能性
3. **低スコアヒット問題** — 関連性の低い結果も返ることがある（閾値チューニングが必要）
4. **stdlib のみ** — 外部依存なしの設計上、高度な NLP 手法（ベクトル検索等）は未実装
5. **単一ファイルロック** — fcntl ベースのファイルロックで並行書き込みを制御（高頻度アクセスには未対応）
6. **search() の副作用** — 検索時に apply_time_decay が書き込みを行う（将来的に読み取り専用パスに分離予定）

## 今後の方向性

1. **ファイル分割** — playbook_api.py が ~1050 行に成長。storage/search/working_memory/cli への分割を検討
2. **セマンティック検索** — TF-IDF の代わりにベクトル検索を導入（SearchBackend インターフェース抽象化）
3. **Playbook 間リンク** — 関連 Playbook の自動推薦
4. **自動昇格** — Inbox 候補の自動評価・昇格パイプライン
5. **VALID_DOMAINS 動的化** — vault 設定ファイルで管理（ハードコード脱却）
6. **マルチ vault 対応** — プロジェクト別 vault の統合検索
