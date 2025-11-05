# Phase 9 実装検証ギャップ 修正計画 (2025-11-05)

## 目的
Phase6〜9 で実装した Session/MCP/CLI 周りでランタイムエラーが残っているため、主要フローを復旧する。

## タスク
1. **VectorDB 呼び出し整合**
   - `ChromaVectorDB` に `collection_name` 引数を追加する、または呼び出し側から除去する。
   - `init_storage` や CLI など全呼び出し箇所で例外が出ないことを確認する。
2. **サービス初期化の引数修正**
   - `IngestionService` に `vector_db` を渡し、`ConsolidationService` に `indexer` を渡す。
   - あわせて未対応パラメータ (`min_cluster_size`, `retention_hours`) の扱いをクラスと一致させる。
3. **SearchService API 補完**
   - `get_memory` と `list_recent` を実装し、MCP/CLI から使用できるようにする。
   - 実装では `vector_db.get` / `list_by_metadata` を使い、必要な整形を行う。
4. **SessionManager 常時有効化**
   - Obsidian 設定の有無にかかわらず SessionManager を初期化し、Vault 連携はフラグで分岐させる。
   - セッション系 MCP ツールがどの構成でも動作することを確認する。
5. **PowerShell ラッパー修正**
   - `setup_cli_recording.ps1` で `start_session` を呼び出し、戻り値の `session_id` を `add_command` でも使い回す。
   - 内部呼び出しフラグや再入防止の動作を再テストする。
6. **テンプレート／CLI 修正**
   - `config.yaml.template` を `load_config` のネスト構造に合わせて更新し、README も最新化する。
   - CLI `consolidate` コマンドを `ConsolidationService.consolidate()` と結び付け、結果が表示できるようにする。

## 検証
- `pytest` とセッション／検索／MCP 周りの主要ユニットテストを再実行する。
- `pytest --cov=src` を流し、カバレッジが低下していないか確認する。
- PowerShell ラッパーは手動またはモックで動作確認する。

## 成功条件
- MCP/CLI のセッション関連コマンドが例外なく動作すること。
- `python -m src.main` が初期化に成功し、待ち受け状態に入ること。
- README とテンプレート更新により、セットアップ手順の齟齬が解消されること。
