# Phase 5 実装補完プラン (2025-11-03)

## タスク概要
1. メタデータ取得基盤の強化
   - ChromaVectorDB: `get` で embedding も返す / `search` に `where` (metadata filter) を適用
   - Indexer: `delete_by_memory_id` が memory_id -> chunk_ids を解決できるようにする
   - SearchService: `_vector_search` で filters を渡す

2. ConsolidationService 実装
   - `_migrate_working_memory`: metadata filter を使って working memory を抽出・更新
   - `_cluster_similar_memories`: memory entry embedding を取得しクラスタリング
   - `_forget_old_memories`: age/importance 条件で削除対象を特定し `Indexer.delete_by_memory_id` を呼ぶ

3. 検索・関連メモリ拡張
   - `get_related_memories`: metadata entry から embedding を取得し類似検索
   - 関連 API の例外・ログ見直し

4. テスト整備
   - ChromaVectorDB へのフィルタ・embedding 取得の単体テスト
   - ConsolidationService の実動テスト (migrate/cluster/forget/representative 選定)
   - Indexer.delete_by_memory_id / SearchService フィルタ・関連メモリのユニットテスト
   - 必要であれば簡易インテグレーション (ingest→consolidate→search)

## 依存関係・進め方
- タスク1が基盤になるため最優先。完了後にタスク2,3を進める。
- タスク2（Consolidation）はタスク1完了後に着手し、状態変化を確認できるようにする。
- タスク3はタスク1完了と並行で着手可能。
- タスク4は各実装タスクと並行で追加するが、最終的にすべてのテストが Phase 5 要件を担保することを確認する。

## 検証方法
- `pytest tests/unit/services/test_consolidation.py` 等で新テストを順次追加しながら実行。
- 必要に応じて仮の in-memory ストレージや fixture を用意し、外部依存を避けて検証する。