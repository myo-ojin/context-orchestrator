# Issue Log - Context Orchestrator

���̃t�@�C���͎����E�^�p���ɔ��������ۑ�𐮗����A�Ή������ƍ���̉��P�v������L���邽�߂̃��O�ł��B

## �^�p���[��
- �V�����ۑ�� **Open Issues** �ɒǉ����AID ����ӂɍ̔Ԃ���B
- �Ή��󋵂��ς������ **Status / Next Action** ���X�V����B������� **Issue Details** �Ɍ����ƑΏ��A�Ĕ��h�~����L�^���������� **Resolved Issues** �ֈړ�����B
- �d�l�ǉ��Ⓑ���v��ɕR�Â��^�X�N�́A���������Ɋւ�炸�ڍ׃Z�N�V�����Ŕw�i�ƃS�[���𖾎�����B

## Open Issues
| ID | Title | Status | Created | Owner | Next Action |
|----|-------|--------|---------|-------|-------------|
| #2025-11-13-09 | ???[???x?[?X???????L???O?{CrossEncoder???????iPhase 4?j | Under Review | 2025-11-13 | ryomy | Phase 6?????????????????p???]?? |
| #2025-11-14-01 | ???I?e?X?g?v?????iPhase 7: Quality Assurance?j | Planned | 2025-11-14 | ryomy | ???l??N?G???p?^?[???A?G?b?W?P?[?X?A????e?X?g?A?i???e?X?g????{ |
## Resolved Issues
| ID | Title | Resolved | Owner | Notes |
|----|-------|----------|-------|-------|
| #2025-11-15-01 | Codex/Claude session logging bridge missing | 2025-11-21 | ryomy | Phase 0-4�����iClaude���S�����C���W�F�X�g�����j�A���r���[�w�E6����+�ă��r���[3����+�ǉ��C��4����+�āX���r���[4���ڐ��������A�����e�X�g�SPASS�iExit Criteria 3/3�B���j�B�ڍׂ� `reports/issue_15-01_review_plan.md` �Q�ƁB|
| #2025-11-13-01 | �������\���̉��P�iEnriched Summary�j | 2025-11-13 | ryomy | Phase 2����: ���ߍ��ݕi��0.910�i?0.80�j�APrecision/NDCG�ێ��APhase 3�ɐi�� |
| #2025-11-11-02 | �������ʂ̍ו����ƃR���e�L�X�g�x�[�X�I�� | 2025-11-14 | ryomy | Phase 6�ő啝���P�B���i���C�e���V71%�팸�ALLM�Ăяo��63%�팸�j�ɂ��s�v�Ɣ��f |
| #2025-11-11-03 | �v���W�F�N�g�������v�[�������ւ̈ڍs | 2025-11-13 | ryomy | Phase 3����: ProjectMemoryPool/warm_cache�����A������ID�t�B���^�����O�@�\�APrecision+136%���P |
| #2025-11-12-01 | �S�������p�t�H�[�}���X�Z�k�� | 2025-11-14 | ryomy | Phase 6�ŒB��: 11.8�b��3.4�b�i71%�팸�j�A5�b�ڕW�ł͂Ȃ������p�\�� |
| #2025-11-11-01 | QAM�����̋L�����^�f�[�^���� | 2025-11-12 | ryomy | Phase 2�L���b�V���œK���ɂ��ڕW���x�B���iP=75.8%, NDCG=1.30�j�AQAM�����͕s�v�Ɣ��f |
| #2025-11-10-07 | �����p�C�v���C���œK����QAM�����g�[ | 2025-11-11 | ryomy | LLM���d���E�L���b�V���œK���� #2025-11-10-06 �ŒB���AQAM������ #2025-11-11-01 �ŕ��j�]�� |
| #2025-11-10-06 | �Z�b�V���������v���W�F�N�g����ƃL���b�V���œK�� | 2025-11-11 | ryomy | 3�w�L���b�V���iL1/L2/L3�j���������A�q�b�g��70%�B���i�ڕW70-80%�j�APhase 3���� |
| #2025-11-05-07 | main.py �Ɗe�N���X�� __init__ �����s��v | 2025-11-05 | TBD | main.py �̌Ăяo������S�ďC�����AMCP �T�[�o�[���N�����邱�Ƃ��m�F |
| #2025-11-05-06 | LocalLLMClient �� embedding/inference ���f�������󂯎��Ȃ� | 2025-11-05 | TBD | __init__ �Ɗe���\�b�h�Ɉ�����ǉ����A�f�t�H���g���f�����𓝈� |
| #2025-11-05-05 | BM25Index �������� main.py �ƕs��v | 2025-11-05 | TBD | main.py �� `index_path` ��n���悤�C�����ABM25 ���� `persist_path` �����e |
| #2025-11-05-04 | ChromaVectorDB �� collection_name ���󂯎��Ȃ� | 2025-11-05 | TBD | �R���X�g���N�^�� collection_name ��ǉ����Amain/cli ����w��\�ɂ��� |
| #2025-11-05-03 | nomic-embed-text-v1.5 ���f�������݂��Ȃ� | 2025-11-05 | TBD | �S 22 �t�@�C���� `nomic-embed-text` �ɒu�����AOllama ���W�X�g���ɍ��킹�� |
| #2025-11-05-02 | SearchService �� get_memory / list_recent ������ | 2025-11-05 | TBD | MCP/CLI ����Ă΂�� 2 ���\�b�h���������A154 �e�X�g���Ď��s |
| #2025-11-03-03 | Phase5 core�T�[�r�X������ | 2025-11-10 | ryomy | ConsolidationService �� migrate/cluster/forget �� main.py �̃X�P�W���[���A�g�������ς� |
| #2025-11-03-01 | Ollama ���ߍ��� API �Ăяo���� 400 �G���[ | 2025-11-03 | TBD | `generate_embedding` �� `input` �L�[�ŌĂяo���悤�C�� |
| #2025-11-03-02 | Chunk ���^�f�[�^�� memory_id ������ | 2025-11-03 | TBD | Chunker/Indexer �� `memory_id` / `chunk_index` �𖄂ߍ��ނ悤���C |
| #2025-11-09-01 | Hybrid search/rerank modernization plan | 2025-11-09 | ryomy | QAM �����Ecross-encoder �ă����N�Etier �� recency �W���݌v�̕��j������ |
| #2025-11-10-01 | �\�����v��e���v�� + ������V�i���I�g�[ + RPC �^�C���A�E�g�Ή� | 2025-11-10 | ryomy | �v��e���v�����V�� load_scenarios ���؁A`--rpc-timeout` �ǉ������� |
| #2025-11-10-02 | �v��e���v�������ƍ\�����؂̎����� | 2025-11-10 | ryomy | README/�V�i���I README �ǋL�� scripts.load_scenarios �̍\�����؃��O�𐮔� |
| #2025-11-10-03 | ���ꌟ�m�� LLM ���[�e�B���O�g�� | 2025-11-10 | ryomy | fallback ���O�v���� CLI override �菇�𐮔� |
| #2025-11-10-04 | �N���X�G���R�[�_�������Ƒ����ꃊ�v���C�g�� | 2025-11-10 | ryomy | reranker LRU �L���b�V���� replay �w�W�𐮔� |

---

### #2025-11-05-07 main.py �Ɗe�N���X�� __init__ �����s��v
- **����**: Phase 8-9 �Ŏ������� main.py ���APhase 1-7 �Œ�`���ꂽ storage/services �Q�̃V�O�l�`����������Ă������߁A���������ɘA���I�� TypeError �������� MCP �T�[�o�[���N���ł��Ȃ������B  
- **�Ώ�**: ModelRouter�AIngestionService�AConsolidationService �ɓn���������Ə�����S�Č������Avector_db �� indexer �̕s�������������B12 �R���|�[�l���g������ɏ���������邱�Ƃ��m�F�ς݁B  
- **�Ĕ��h�~**: �d�l�t�F�[�Y���ƂɎ��ۂ̋N���e�X�g���s���A�e�N���X�̃V�O�l�`�������� issue �����Ă���C������B

### #2025-11-05-05 BM25Index �̈������� main.py �ƕs��v
- **����**: main.py �� `index_path` ��n���̂ɑ΂��ABM25Index �� `persist_path` �����҂��Ă������ߏ������Ɏ��s�B  
- **�Ώ�**: main.py ���ŃL�[�����C�����ABM25 ��������݊��� `index_path` ���󂯕t����悤�ɂ����B  
- **�⑫**: ������ settings ����̃p�X�w��~�X�������� grep �Ŋm�F�B

### #2025-11-05-04 ChromaVectorDB �� collection_name ���󂯎��Ȃ�
- **����**: main/cli ����R���N�V��������n���Ȃ����߁A�����e�i���g�̕��s�^�p���ł��Ȃ������B  
- **�Ώ�**: `collection_name` ������ǉ����A�f�t�H���g�l�� config �Ɠ����B  
- **����**: CLI �� MCP �o���ŋN�����A�قȂ�R���N�V���������w�肵���ۂɏՓ˂��Ȃ����Ƃ��m�F�B

### #2025-11-05-03 nomic-embed-text-v1.5 ���f�������݂��Ȃ�
- **����**: 22 �t�@�C���� `nomic-embed-text-v1.5` ���Q�Ƃ��Ă������AOllama ���ɊY�����f�����Ȃ��S�Ă̖��ߍ��݌Ăяo�������s�B  
- **�Ώ�**: ���ׂ� `nomic-embed-text` �ɒu�����AREADME �� scripts �������ɓ���B  
- **�Ĕ��h�~**: �V���f�����g���ۂ͌������W�X�g���ő��݊m�F���Ă��瓱������B

### #2025-11-05-02 SearchService �� get_memory / list_recent ������
- **����**: MCP �v���g�R���� CLI �� `get_memory` �� `list_recent` ���Ăяo���Ă������ASearchService �Ɏ������Ȃ� runtime error �ɂȂ��Ă����B  
- **�Ώ�**: VectorDB �� `get` / `list_by_metadata` �𗘗p���� 2 ���\�b�h�������B154 �e�X�g�����s���A�����@�\�ւ̉e�����������Ƃ��m�F�B  
- **�Ĕ��h�~**: Handler ����V���\�b�h���ĂԑO�ɃT�[�r�X�w�� stub ��p�ӂ���B

### #2025-11-03-03 Phase5 core�T�[�r�X������
- **����**: Phase5 �őz�肵�Ă��� Consolidation/�폜�t���[���������̂܂܎c��ASession/Fuse �A�g�����삵�Ȃ������B  
- **�Ώ� (2025-11-10)**: ConsolidationService.consolidate() �� _migrate_working_memory �� _cluster_similar_memories �� _process_clusters �� _forget_old_memories �����Ɏ��s���銮�S�p�C�v���C����񋟂��Amain.py �� init_services / check_and_run_consolidation / APScheduler �����Ԏ��s�� 24 ���ԊĎ����s���\���ɍX�V�B�폜�t�F�[�Y�ł� Indexer.delete_by_memory_id �ɂ�� chunk �ꊇ�폜�� SearchService �̃��^�f�[�^�t�B���^�Ő�������ۂB  
- **����**: pytest 69 passed / 10 skipped�Apytest --cov=src 61% �ɉ����A�蓮���s�� Consolidation ���v���O�� scheduler �� timestamp �X�V���m�F�ς݁B  
- **�Ĕ��h�~**: Consolidation ���v�� LLM �N���C�A���g�w�̃��W���[���������r���[���APhase6 �ȍ~�̋@�\�ǉ����� CLI/MCP �N���e�X�g��K�{������B  

### #2025-11-09-01 Hybrid search/rerank modernization plan
- **�w�i**: timeline �� change-feed �̂悤�Ȗ��m�ȃN�G���� working/short-term ��������ɏ�ʂ�苒���A�K�v�Ȓ����������������BBM25 ���������� chunk ���T�}������ɗ���ꍇ�����݁B  
- **�O���x�X�g�v���N�e�B�X**: QAM �ɂ��N�G���������o�AHYRR �̂悤�� dense+BM25 �n�C�u���b�h�ACLEF CheckThat! 2025 �� cross-encoder ���p�ACaGR-RAG �̃N�G���N���X�^�����O�ɂ�� tail latency �팸�B  
- **Next Actions**:  
  1. LLM �� topic/type/project �����𒊏o�� SearchService �̃t�B���^/metadata bonus �ɓK�p�B  
  2. dense100 + BM25 30 �̌��� cross-encoder �ɓn���A�������[�� `_rerank` �̓t�H�[���o�b�N���B  
  3. tier ���Ƃ� recency �W���𒲐����A��������������ł���悤 `_calculate_recency_score` ���Đ݌v�B  
  4. chunk �������L���O�Ώۂ���O���A�̗p�����̕⑫���Ƃ��Ă̂ݕԂ��B  
  5. `scripts.mcp_replay` �� Precision/NDCG �������v�����A�g�s�b�N�P�ʂɃo�b�`�������� IO ���œK���B

### #2025-11-10-01 �\�����v��e���v�� + ������V�i���I�g�[ + RPC�^�C���A�E�g�Ή�
- **����**: �v�񂪎��R�`���� Topic/DocType/Project ��񂪌������₷���A������V�i���I���s���B�܂� `scripts.mcp_replay` ���d���N�G���Ń^�C���A�E�g���Ă����B  
- **�Ή� (2025-11-10)**:  
  1. `src/services/ingestion.py` ���\�����e���v�� (Topic/DocType/Project/KeyActions) + ������q���[���X�e�B�N�X + �Ď��s/�t�H�[���o�b�N�t���ɍ��V�B  
  2. `tests/scenarios/scenario_data.json` �ɓ��{��E�X�y�C����E�p�ꍬ�݃P�[�X��ǉ����A`tests/unit/services/test_ingestion_summary.py` �Ńt�H�[�}�b�g���؂��������B  
  3. `scripts/mcp_replay.py` / `scripts.run_regression_ci.py` �� `--rpc-timeout` ��ǉ����A�N���E�h LLM �⑽����N�G���ł� CI ����������悤�ɂ����B  
- **����**: `python -m scripts.run_regression_ci --rpc-timeout 60` �� Macro Precision 0.667 / Macro NDCG 0.893�A�[���q�b�g 0 ���i`reports/mcp_runs/mcp_run-20251110-000125.jsonl`�j�B  
- **�Ĕ��h�~**: ���v�����v�g�� `docs/prompts/legacy_ingestion_summary.txt` �ɑޔ����A�e���v���ύX��ǐՂł���悤�ɂ����B

### #2025-11-10-02 �v��e���v�������ƍ\�����؂̎�����
- **����**: KeyActions ���i����ԍ��t���ŏo�͂����P�[�X������A�V�i���I�Ď�荞�ݎ��Ɉُ���������Ă����B  
- **�Ώ� (2025-11-10)**: README / tests/scenarios/README �Ƀt�H�[�}�b�g�K��ƕ����菇��ǋL���Ascripts/load_scenarios.py �����؎��s���Ƀ��� ID�E�v�񔲐��E�����e���v�����܂ރG���[���O���o���đ���~����悤�X�V�B  
- **����**: 	ests/unit/services/test_ingestion_summary.py �ŉӏ������e���v���̐���n/�t�H�[���o�b�N�n���ێ����A���[�_�[�o�R�ł����� is_structured_summary �t���[���g�����Ƃŕs���T�}���� ValueError �ɂȂ邱�Ƃ��m�F�i���O���e��ǉ��Ń`�F�b�N�j�B  
- **�Ĕ��h�~**: ���[�_�[�� CI �̑o���Ńe���v�����؂��s���A�ŐV�Ńe���v���ƃ��J�o���[�菇�� README �Q�ɕK���L�ڂ���^�p�֓���B  

### #2025-11-10-03 ���ꌟ�m�� LLM ���[�e�B���O�g��
- **����**: langdetect �ɂ�鎩������͓����ς݂��������A�N���E�h LLM �ւ̃t�F�[���I�[�o�[���������Ă����C�e���V���v���ł����ACLI ���猾������������i�����������B  
- **�Ώ� (2025-11-10)**: IngestionService �� `LanguageRoutingMetrics` ��ǉ����ăN���E�h�o�H�̏�������/���s�����L�^���Afallback �������� `Language routing fallback (lang=...)` ���O�֏o�́B����Ɋ��ϐ� `CONTEXT_ORCHESTRATOR_LANG_OVERRIDE` �� conversation metadata ���猾����㏑���ł���悤�ɂ��AREADME �� override �菇��ǋL�B  
- **����**: `CONTEXT_ORCHESTRATOR_LANG_OVERRIDE=fr` ��ݒ肵����ԂŃV�i���I���Đ����A���O�� 2 �񕪂� fallback ���C�e���V���o�͂���邱�ƁA����� `tests/unit/services/test_ingestion_summary.py` ���p�����Ēʉ߂��邱�Ƃ��m�F�B  
- **�Ĕ��h�~**: �t�H�[���o�b�N�Ď��� override �菇�� README/config �e���v���ɂ��K�����L���A���ニ�[�e�B���O���X�V����ۂ͓����v���t�b�N���ێ�����B  
### #2025-11-10-04 �N���X�G���R�[�_�������Ƒ����ꃊ�v���C�g��
- **����**: �A�����v���C�œ��� (query, memory_id) �����x�� LLM �ɓ����Ă���A8?11 �b�̑҂����ԂƃR�X�g���������B`query_runs.json` ���p��݂̂��������߁A���ꃋ�[�e�B���O���ׂ����Č����`�F�b�N���ł��Ȃ������B  
- **�Ώ� (2025-11-10)**: `CrossEncoderReranker` �� LRU �L���b�V���i�T�C�Y/TTL �� config �Ő���j�ƃ��C�e���V���v���������A`get_reranker_metrics` MCP �c�[���o�R�Ńq�b�g�����擾�ł���悤�ɂ����B����� `scripts.mcp_replay` �Ń��v���C�I����Ƀ��g���N�X��₢���킹�A�uReranker Metrics�v�Ƃ��� stdout / JSONL �ɋL�^�B`tests/scenarios/query_runs.json` �ɂ͓��{��/�X�y�C����̃N�G����ǉ����A�����ꃋ�[�e�B���O�ƃL���b�V���������������؂���悤�ɂ����B  
- **����**: `python -m scripts.mcp_replay --requests tests/scenarios/query_runs.json` �����s���A`cache_hit_rate` �� LLM ���C�e���V���\������邱�ƁA�����N�G���� 2 �񗬂��Ă� LLM �Ăяo�����������Ȃ����Ƃ��m�F�B  
- **�Ĕ��h�~**: reranker �֘A�̐ݒ�� README / config �e���v���ɕK���ǋL���ACI �ł� `get_reranker_metrics` �����ăq�b�g���E���s�����Ď�����B  

### #2025-11-10-05 �f�[�^�h���u���ă����N�d�݊w�K
- **����**: ���[���x�[�X�̏d�݂��o�����̂܂܂ŁA���x���P�̗]�n�������Ă������������Ē����ł��Ȃ������Breplay �œ�����e�R���|�[�l���g�̍v���x���L�^����Ă��炸�A�w�K�f�[�^������i���Ȃ������B  
- **�Ώ� (2025-11-10)**: `scripts.mcp_replay` �� `--export-features` ��ǉ����A�e���ʂ� `memory_strength/recency/bm25/vector/metadata` �� CSV �փG�N�X�|�[�g�ł���悤�ɂ����B`scripts/train_rerank_weights.py` �� CSV ��ǂݍ��݁A�P�����W�X�e�B�b�N��A�Ɋ�Â��d�݂��w�K���� `config.reranking_weights` �ɏ����߂���悤�ɂ����BSearchService �� config �̏d�݂�ǂݍ���ŃX�R�A�v�Z�ɗ��p���Ametadata bonus ���X�P�[���u���ɂ����B  
- **����**: ������ CSV ���쐬 �� �w�K�X�N���v�g�ŏd�݂��o�� �� config.yaml ���X�V �� `python -m scripts.run_regression_ci` �����s���APrecision/NDCG �Ɍ�ނ��Ȃ����Ƃ��m�F�B  
- **�Ĕ��h�~**: reranking_weights �̍X�V�菇�� README �ɒǋL���ACI �ł� `--export-features`�{`train_rerank_weights` �̗���ō����̂���d�݂𓾂邱�Ƃ����[��������B

### #2025-11-10-06 �Z�b�V���������v���W�F�N�g����ƃL���b�V���œK��
- **�ړI**: �V�K�Z�b�V�����ł� project_id ����̂܂܎n�܂�A�v��/����/�L���b�V���Ƀv���W�F�N�g�������f����Ȃ��B
- **�v����**:
  1. SessionManager �� project_hint ��ǉ����ACLI/Obsidian �̃��^�f�[�^�� QueryAttributeExtractor �̌��ʂ���i�K�I�ɐ��肷��B
  2. �M���x��臒l�𒴂������b metadata �� project_id �������t�^���A�v��e���v���ESearchService�ECrossEncoder reranker �֔��f����B
  3. ���[�U�[�� session set-project <name> �Ȃǂŏ㏑���ł���悤�ɂ��A�C�����ʂ��q���[���X�e�B�b�N�����փt�B�[�h�o�b�N����B
  4. �v���W�F�N�g�m�莞�� search_in_project ���v���t�F�b�`���ăn�C�v���I�����L���b�V���ɍڂ��A�L���b�V���q�b�g�������コ����B
  5. ���胍�O�i����l/�M���x/�C�������j���o�͂��A���x�������r���[����B
- **�i�� (2025-11-11 �ߑO)**:
  - SessionManager �� `ProjectPrefetchSettings` �� SearchService �Q�Ƃ�ǉ����Aproject_hint ��臒l�𒴂����u�Ԃ� `prefetch_project` ����x�������s����t�b�N�������Bprefetch �����E���s���O���ێ����Č㑱���͂ł����Ԃɂ����B
  - SearchService ���� `prefetch` �t���O�t���� search_in_project / cross-encoder �Ăяo���� `prefetch_project` API �������BCrossEncoderReranker �̃��g���N�X�� `prefetch_requests/hits/misses` ��ǉ����A`scripts/mcp_replay` �ŉ����ł���悤�ɂ����B
  - config/template �Ƀv���t�F�b�`�p�p�����[�^��ǉ����AMCP �V�i���I `tests/scenarios/query_runs.json` �ƃ��j�b�g�e�X�g�isession_manager / search_service_rerank / rerankers�j���g���B
  - **�e�X�g���ʁi.venv311���j**: �S35���̃��j�b�g�e�X�g���p�X�B��A�e�X�g�������iPrecision 0.712, NDCG 1.310�j�B
- **�ڍו��� (2025-11-11 �ߌ�)**:
  - **�������x**: �x�[�X���C������啝���P�iPrecision +90%, NDCG +148%�j�A�[���q�b�g0���B
  - **�L���b�V���q�b�g��**: 11%�i�ڕW60%�ɖ��B�j
    - ���X�R�A�����O�y�A: 79���i22�N�G�� + 6�v���t�F�b�`�j
    - LLM�Ăяo��: 70���i�L���b�V���~�X�j�A�L���b�V���q�b�g: 9��
    - �v���t�F�b�`: 6����s�A18�y�A���X�R�A�����O�������q�b�g0
  - **���{��������**:
    1. **���S��v�v��**: �L���b�V���L�[�� `query::project_id::candidate_id` �ŁA�N�G�������S��v���Ȃ��ƃq�b�g���Ȃ�
    2. **�N�G���̕s��v**: �v���t�F�b�`�N�G���i"project status", "open issues"�j�Ǝ��ۂ̃N�G���i"change feed", "dashboard pilot"���j���S���قȂ�
    3. **���ID�̉e��**: �����N�G���ł��������ʂ��قȂ�΃L���b�V���L�[���قȂ�
    4. **TTL�Z��**: 900�b�i15���j�ł͍�ƃZ�b�V�������ɂ������؂�̉\��
  - **���P�v��i3�t�F�[�Y�j**:
    - Phase 1: TTL�����i8���ԁj+ �L���b�V���T�C�Y�g��i256�j�� ���҃q�b�g�� 18-22%
    - Phase 2: �L�[���[�h�x�[�X�L���b�V���i�d�v��b���o�ŕ����}�b�`�j�� ���҃q�b�g�� 45-55%
    - Phase 3: �Z�}���e�B�b�N�ގ��x�x�[�X�L���b�V���i���ߍ��ݗގ��x>0.85�Ńq�b�g�j�� ���҃q�b�g�� 70-80%
  - **�������e��**: 8����TTL�ł��ő�7MB�i�V�X�e���S�̂�0.2%�����j�A�p�t�H�[�}���X�ቺ�Ȃ��i�S����O(1)�j
- **�i�� (2025-11-11 �ߌ�)**:
  - Phase 1����: TTL�����i28800�b/8���ԁj�A�L���b�V���T�C�Y�g��i256�j
  - **Phase 2���� (2025-11-11 �[��)**: �L�[���[�h�x�[�X�L���b�V������
    - **�������e**:
      - `src/utils/keyword_extractor.py`: �L�[���[�h���o���[�e�B���e�B�i161�s�A�p���Ή��A�X�g�b�v���[�h�t�B���^�����O�j
      - `CrossEncoderReranker`: L1�i���S��v�j+ L2�i�L�[���[�h�����}�b�`�j��2�w�L���b�V��
      - `_build_keyword_cache_key()`: Top 3�L�[���[�h����\�[�g�ς݃V�O�l�`������
      - `_score_with_cache()`: L1 �� L2 �� LLM �t�H�[���o�b�N���W�b�N
      - ���g���N�X�ǉ�: `keyword_cache_hits/misses`, `keyword_cache_hit_rate`, `total_cache_hit_rate`
    - **�e�X�g����**:
      - ���j�b�g�e�X�g: 29���S�ăp�X�ikeyword_extractor 24�� + reranker 5���j
      - **�������ʑ���** (`test_keyword_cache.py`):
        - �x�[�X���C��: 11%
        - **Phase 2������: 28.57%**�i2.6�{���P�I�j
        - L1�i���S��v�j: 25% hit rate�i1/4�j
        - L2�i�L�[���[�h�j: 33.33% hit rate�i1/3�j
        - LLM�Ăяo��: 4�N�G����2��̂݁i���Ғʂ�j
    - **�L�[���[�h���o����**:
      - "change feed ingestion errors" �� `change+errors+ingestion`
      - "ingestion errors in change feed" �� `change+errors+ingestion`�i����V�O�l�`���I�j
      - "errors in change feed ingestion" �� `change+errors+ingestion`�i����V�O�l�`���I�j
      - �ꏇ���قȂ�N�G���ł������L�[���[�h�𐳂������o���AL2�L���b�V���q�b�g����
    - **���ӎ���**: MCP replay�ł̊��S����͖����{�i�T�[�o�[�ċN�����K�v�j
  - ��: Phase 3�i�Z�}���e�B�b�N�ގ��x�x�[�X�j�̎���
- **�o������**: �ŏI�I�ɃL���b�V���q�b�g�� 70-80%�A���ό������C�e���V 0.3�b��B�����邱�ƁB

### #2025-11-11-01 QAM�����̋L�����^�f�[�^����
- **�w�i**: QueryAttributeExtractor�iQAM�j�́ALLM���g���ăN�G������topic/doc_type/project_name/severity�����𒊏o���A���^�f�[�^�{�[�i�X�i�ő�+0.10�j��t�^����@�\�BPhase 15�Ŏ������ꂽ���ALLM�t�H�[���o�b�N���p�����A28�N�G���~3.3s/call = 92.4�b�̗ݐϒx���������N�����Ă����iissues.md �^�C���A�E�g���� 2025-11-11�j�B
- **�Ώ� (2025-11-12)**:
  - QAM�������ɂ�茟�����x���ĕ]��: Macro Precision 75.8%, Macro NDCG 1.30�i�ڕW?65%/?0.85��啝���߁j�A�[���q�b�g0��
  - Phase 2�L���b�V���œK���iKeyword-based L2 cache�j�ɂ��A28.57%�̃q�b�g���B���i�N�G���o���G�[�V�����z���j
  - Cross-encoder reranking����v�ȃ����L���O���P��S�����AQAM�Ȃ��ł��\���@�\
  - �R�X�g�x�l�t�B�b�g����: �R�X�g�i3.3�b/�N�G���j���x�l�t�B�b�g�i+0.10�̃��^�f�[�^�{�[�i�X�j��啝�ɏ���
- **���_**: QAM�����͕s�v�BPhase 2�L���b�V���œK����Cross-encoder reranking�ɂ��AQAM�Ȃ��ŖڕW���x��B���BLLM�R�X�g�ƃ��C�e���V���l�����A������������B
- **�ĕ]���g���K�[**: �������x��60%����������ꍇ�A�܂��͌y�ʂȃN�G���������o��@�i<100ms�j�����p�\�ɂȂ����ꍇ�ɍČ����B
- **�֘A�R�[�h**: src/services/search.py:336-350�i_extract_query_attributes �͏�� None ��Ԃ��j

### #2025-11-11-03 �v���W�F�N�g�������v�[�������ւ̈ڍs�i�i�K�I�k�ރ��[�N�t���[�j
- **�w�i**: ����̃v���t�F�b�`�i����N�G���ŃL���b�V���E�H�[�~���O�j�́A�N�G���x�[�X�̃L���b�V���L�[�i"query::project_id::candidate_id"�j�̂��߁A���ۂ̃N�G���ƈقȂ�ƑS���q�b�g���Ȃ��B#2025-11-10-06�ŋL�^: �v���t�F�b�`6����s�A18�y�A���q�b�g0�B�l�J���҂͐�����?�����ԁA����v���W�F�N�g�ɏW����Ƃ��邽�߁A�v���W�F�N�g�X�R�[�v�ł̋L�������O�L���b�V������Α啝�ȃq�b�g�����P�����҂ł���B
- **�v���g�^�C�v���� (2025-11-12)**:
  - **Phase 1: �ŏ��@�\�Z�b�g** - ���ʌ��ؗp�v���g�^�C�v
  - **�������e**:
    1. `ProjectMemoryPool` �N���X (280�s): �v���W�F�N�g�L���̈ꊇ���[�h��embedding���O����
    2. `CrossEncoderReranker.warm_semantic_cache_from_pool()` (+48�s): L3�L���b�V���ւ̒��ړ���
    3. `SessionManager` ���� (+24�s): �v���W�F�N�g�m�莞��warm_cache�������s
    4. �P�̃e�X�g12��: �S�ăp�X (1.58s)
  - **�@�\�t���[**:
    1. �v���W�F�N�g�m��i�M���x>0.75�j�� ProjectMemoryPool.load_project()
    2. �v���W�F�N�g�̑S�L���擾�i�ő�100���ATTL=8���ԁj
    3. �e�L����embedding���O����
    4. CrossEncoder��L3�Z�}���e�B�b�N�L���b�V���ɓ����i�N�G����ˑ��j
    5. �ȍ~�̌�����embedding�ގ��x>0.85�ŃL���b�V���q�b�g
  - **���،���**: warm_cache�����ɒv���I�o�O�����i�������R���e���cembedding��L3�L���b�V���ɓ����A�N�G��embedding�Ɣ�r���邽�ߖ��Ӗ��j
- **�A�[�L�e�N�`���Č��� (2025-11-12)**:
  - **���肵�����[�N�t���[**: �i�K�I�k�ރ��[�N�t���[A�i���񏈗���胊�\�[�X�����D��j
  - **�V���[�N�t���[**:
    ```
    �v���W�F�N�g�m��
      ��
    �������v�[���擾�i30���j
      ��
    L1/L2/L3�`�F�b�N�i30���ɑ΂��āj
      �� �L���b�V���~�X
    LLM���������v�[���������i30���A3����j
      �� ���ʕs���i<top_k�j
    �S�������i100���j
      ��
    L1/L2/L3�`�F�b�N�i100���ɑ΂��āj
      �� �L���b�V���~�X
    LLM���S�������i100���A3����j
    ```
  - **�\���p�t�H�[�}���X�i3������s�j**:
    - �P�[�X1�i�v���W�F�N�g���ŏ\���A70%�j: 21.2�b
    - �P�[�X2�i�S�������K�v�A25%�j: 89.4�b
    - �P�[�X3�i�v���W�F�N�g���m��A5%�j: 68.2�b
    - **�d�ݕt������: 40.6�b/�N�G��**�i�]��118.1�b����66%�Z�k�j
  - **���񏈗���r**: ���[�N�t���[B�i������s�j��42.8�b/�N�G���AA��5%����
  - **Phase 2�������e**:
    1. `ProjectMemoryPool.get_memory_ids()`: �v���W�F�N�g�̃�����ID�Z�b�g�擾
    2. `SearchService.search_in_project()`: �������v�[���t�B���^�����O����
    3. ���ʕs�����胍�W�b�N�i`len(results) < top_k`���X�R�A臒l�l���j
    4. ���[�U�[�t�B�[�h�o�b�N�i�u�ǉ�������...�v�j
- **Phase 2���������E���ʌ��� (2025-11-12)**:
  - **�����T�}���[**:
    - �t�@�C���ύX: 4�t�@�C���iproject_memory_pool.py, search.py, main.py, issues.md�j
    - �ǉ��R�[�h: 210�s�ihelper methods 3�� + search_in_project rewrite�j
    - �o�O�t�B�b�N�X: main.py�����������C���iProjectMemoryPool �� SearchService�j
    - �e�X�g����: ���j�b�g�e�X�g12/12�p�X�A��A�e�X�g���i
  - **�������x**: ? **�啝���P**
    - Macro Precision: 0.375 �� **0.841** (+124%)
    - Macro NDCG: 0.528 �� **1.243** (+135%)
    - �[���q�b�g: **0��**�i�����j
  - **�p�t�H�[�}���X**: ?? **�ڕW���B**
    - LLM�Ăяo��: **59��**�i�ڕW?20��A��+39��j
    - �L���b�V���q�b�g��: **11%**�i�ڕW?14%�A��-3%�j
    - Prefetch�q�b�g��: **0%**�i0/18�y�A�j
  - **���{��������**:
    1. **Prefetch�@�\�s�S**: �v���W�F�N�g�����F���͓���i4�v���W�F�N�g�A�M���x0.9�j���Ă��邪�Awarm_cache()���Ă΂�Ă��Ȃ��A�܂��̓v�[�����O���[�h���x�����s����Ă���
    2. **�L���b�V���~�X�}�b�`**: Prefetch�N�G���i"project status"���j�Ǝ��ۂ̃N�G���i"change feed"���j������
    3. **LLM�ҋ@����**: ����2570ms�A�ő�11061ms�i4�{�̂΂���j
  - **���̃A�N�V����**:
    - �D��x��: Prefetch�@�\�̃f�o�b�O�iSessionManager.set_project_hint()��warm_cache()�̌Ăяo���^�C�~���O�m�F�j
    - �D��x��: Prefetch�N�G�������ۂ̎g�p�p�^�[���ɍ��킹�Ē���
    - �D��x��: �L���b�V���E�H�[�~���O�헪�̌�����
- **warm_cache���� (2025-11-12 �ߌ�)**:
  - **�������e**:
    - SearchService.prefetch_project()�Ƀf���A���헪�L���b�V���E�H�[�~���O�ǉ�
      - Step 1: ProjectMemoryPool.warm_cache() �� L3�Z�}���e�B�b�N�L���b�V���i�N�G����ˑ��j
      - Step 2: Prefetch�N�G�����s �� L1/L2�L���b�V���i�N�G���ˑ��j
    - SessionManager._maybe_trigger_project_prefetch()�̃R�����g�X�V
    - �t�@�C���ύX: search.py (+95�s), session_manager.py (+4�s)
    - �e�X�g����: ���j�b�g�e�X�g�S�ăp�X
  - **��A�e�X�g���ʁiwarm_cache������j**:
    - Macro Precision: 0.841�i�ω��Ȃ��j
    - Macro NDCG: 1.243�i�ω��Ȃ��j
    - LLM�Ăяo��: 59��i�ω��Ȃ��j
    - �L���b�V���q�b�g��: 11%�i�ω��Ȃ��j
    - Prefetch�q�b�g��: 0/18�i�ω��Ȃ��j
    - **���P�_**: ����LLM�ҋ@ 2570ms��2313ms (-10%)�A�ő�LLM�ҋ@ 11061ms��3832ms (-65%)
  - **���ʖ��m�F�̌�������**:
    1. **�e�X�g�V�i���I�s��**: ���݂�query_runs.json�͓���v���W�F�N�g���̋L���ƃN�G�������Ȃ�
    2. **������ID�t�B���^�����O���ʂ���**: ���100��30�팸�͊��ɋ@�\���Ă��邪�Awarm_cache�̌��ʂ͑���ł��Ă��Ȃ�
    3. **L3�L���b�V���̎d�g�݊m�F**: ������embedding�����ID���ƂɊi�[���A�N�G��embedding�Ƃ̗ގ��x?0.85�ŃL���b�V���q�b�g�i�݌v�͐������j
  - **���̌��؃X�e�b�v**:
    - Phase 3a: ������ID�t�B���^�����O���ʂ̒�ʑ���i���O���́j?
    - Phase 3b: �e�X�g�V�i���I�g�[�i����v���W�F�N�g���̋L��30��+�N�G��15���ǉ��j?
    - Phase 3c: warm_cache���ʂ̍đ��� ?
- **Phase 3a-c ���{���� (2025-11-13)**:
  - **Phase 3a: ������ID�t�B���^�����O���ʑ���**:
    - ���O����m�F: `Pool filtering: 100��30 candidates`�i70%�팸�j������ɋ@�\
    - �t�B���^�����O���W�b�N�͑z��ʂ蓮��
  - **Phase 3b: �V�i���I�g�[**:
    - AppBrain��b: 8��38���i+30���j
    - AppBrain��p�N�G��: 0��15���i�V�K�ǉ��j
    - ����b��: 60��82���A���N�G����: 28��43��
    - expand_appbrain_scenarios.py�Ŏ��������iArchitecture 5, Code 10, Ops 5, Config 5, Testing 5�j
  - **Phase 3c: warm_cache�đ��茋��**:
    - **�e�X�g����**: PASSED�AZero-hit queries 0��
    - **�������x�啝���P**:
      - Macro Precision: 0.375��0.841 (+124%)
      - Macro NDCG: 0.528��1.345 (+155%)
    - **�v���W�F�N�g�q���g���퓮��**: AppBrain, InsightOps, PhaseSync, BugFixer���������o
    - **LLM�Ăяo���팸����**: 64��i�ڕW20��ȉ��ɑ΂����B�j
    - **�L���b�V�����ʖ��m�F**:
      - Cache hit rate: 10%�i�ڕW60%���B�j
      - Prefetch hit rate: 0% (0/18)
      - Avg LLM latency: 8318ms
  - **warm_cache���ʂ��o�Ȃ���������**:
    1. **�L���b�V���L�[�~�X�}�b�`**: L3�L���b�V����`(query_embedding, candidate_id)`�����Awarm_cache()�o�^���̃L�[����v���Ă��Ȃ��\��
    2. **�N�G��embedding�s��**: warm_cache���ɂ̓N�G��embedding�����݂��Ȃ����߁A������embedding�����o�^���Ă��������Ƀ}�b�`�ł��Ȃ�
    3. **Similarity threshold�ߑ�**: �R�T�C���ގ��x?0.85������������\��
  - **Phase 3d: �ڍ׃f�o�b�O�������� (2025-11-13 01:30)**:
    - **���{����1: `filter_dict`�����G���[**
      ```
      ERROR: ChromaVectorDB.list_by_metadata() got an unexpected keyword argument 'filter_dict'
      ```
      - `ProjectMemoryPool.load_project()`�����s���Awarm_cache��0���̃������Ŏ��s����Ă���
      - �C���ӏ�: `src/services/project_memory_pool.py:107` ��`filter_dict`���������m�F�E�C��
    - **���{����2: �ގ��x��臒l���B�i�݌v��̌��E�j**
      - L3_CHECK���O����m�F�����ގ��x:
        - `similarity=0.592` (臒l0.85�����A69%)
        - `similarity=0.447` (臒l0.85�����A53%)
        - `similarity=0.553` (臒l0.85�����A65%)
        - `similarity=0.397` (臒l0.85�����A47%)
      - **�S�Ă̗ގ��x��0.85��傫�������**
      - ���R: **�N�G��embedding�ƃ�����embedding�͈Ӗ��I�ɈقȂ�**
        - ������embedding: �L�����e�S�̂�\���i��: "AppBrain��release checklist�S��"�j
        - �N�G��embedding: ���[�U�[�̎���Ӑ}�i��: "AppBrain release gating checklist"�j
        - ���҂̃R�T�C���ގ��x�͍ō��ł�0.6���x�ŁA0.85�ɂ͓͂��Ȃ�
    - **���_**: warm_cache�ɂ��**�N�G����ˑ���L3�L���b�V��**�͐݌v��̌��E������A���ʂ͌���I
  - **���̃A�N�V�����āi�D��x���j**:
    - **Option B (�ŗD�搄��)**: Workflow A���S����
      - �v�[����������D�悵�A���ʕs�����̂ݑS�������Ƀt�H�[���o�b�N
      - ������ID�t�B���^�����O���ʁi100��30���A70%�팸�j���ő�����p
      - ����ɂ��LLM�Ăяo������30���ȉ��ɍ팸�\
      - warm_cache�̌��ʂɈˑ������A�m����LLM�팸���B���ł���
    - **Option C**: Prefetch�N�G���̐��x����
      - ���ۂ̎g�p�p�^�[���ɋ߂��N�G����prefetch_queries�ɒǉ�
      - �v���W�F�N�g�ŗL�̕p�o�N�G����config.yaml�Őݒ�\�ɂ���
      - ������L1/L2�L���b�V���őΉ��i�N�G��embedding�x�[�X�j
    - **Option A**: �ގ��x臒l��0.6�ɉ�����
      - warm_cache���@�\����悤�ɂȂ邪�A���x�ቺ�̃��X�N����
      - �񐄏��i���̃I�v�V�����̕������ʓI�j
- **�o������**: �������v�[���t�B���^�����O�ɂ��LLM�Ăяo��70%�팸�A�L���b�V���q�b�g��14%�ێ��APrecision?84%�ێ�
  - ? �������v�[���t�B���^�����O: �@�\�m�F�ς݁i100��30���A70%�팸�j
  - ? LLM�Ăяo���팸: ���B�i66��A�ڕW20��j
  - ? Precision�ێ�: 82.6%�i�ڕW84%�قڒB���j
  - ? �L���b�V���q�b�g��: 10%�i�ڕW14%���B�j
  - **���_**: warm_cache�����͋Z�p�I�Ɏ��������������AL3�L���b�V���̐݌v��̐���ɂ����ʂ�����I�B**Option B�iWorkflow A���S�����j��D�悷�ׂ�**
- **Phase 3e: �o�O�C����warm_cache����m�F (2025-11-13 �ߌ�)**:
  - **���{�����C���i4���j**:
    1. `filter_dict` �� `filter_metadata` (project_memory_pool.py:108)
    2. �����L�[�t�B���^�����O��$and���Z�q�T�|�[�g (vector_db.py:229-234)
    3. `_merge_candidates` �� `_merge_results` (search.py:1387)
    4. `_rerank_with_cross_encoder` �� `_rerank` + `_apply_cross_encoder_rerank` (search.py:1401-1416)
  - **���،���**:
    - ? ���j�b�g�e�X�g: 12/12 passed (ProjectMemoryPool)
    - ? �v�[�����[�h����: **100 memories loaded** (�ȑO��0)
    - ? warm_cache����: **100 embeddings stored** in L3 cache
    - ? L3�L���b�V���`�F�b�N����: �ގ��x0.39-0.72���v���i臒l0.85�����j
    - ? Prefetch����: 3/3�N�G�����s�Apool=100 memories
    - ? L3�L���b�V���q�b�g��: **0%** (�S��臒l���B)
  - **�m�F���ꂽ�݌v��̐���**:
    - �N�G��embedding vs ������embedding�̗ގ��x: 0.39-0.72�i����0.55�j
    - 臒l0.85�ɂ͓͂��Ȃ��iissues.md:302-310�ŗ\���ς݁j
    - warm_cache�͋Z�p�I�ɐ��퓮�삵�Ă��邪�A�ގ��x�̐�����A���ʂ͌���I
  - **���_**:
    - ProjectMemoryPool/warm_cache�̎�����**�Z�p�I�Ɋ���**
    - �v�[���T�C�Y0��100�ւ̉��P�ɂ��A������ID�t�B���^�����O�i100��30���j���@�\
    - L3�L���b�V���̌��ʂ͌���I�����A�v�[���t�B���^�����O�ɂ��LLM�팸�͎����\
    - **���̗D��A�N�V����**: issues.md:313-317��Option B�iWorkflow A���S�����j�𐄏�
      - �v�[����������D�悵�A���ʕs�����̂ݑS������
      - ������ID�t�B���^�����O���ʂ��ő劈�p
      - LLM�Ăяo������30���ȉ��ɍ팸�i�ڕW�B���\�j
- **Phase 3f: L3�L���b�V����ގ��x�̍��{�������� (2025-11-13 ��)**:
  - **�����̌o��**:
    - Phase 3e�ŗގ��x0.39-0.72���m�F�������A�����embedding���f���̖�肩�݌v��̖�肩���s��
    - ���[�U�[����u�x�N�g��������������ł��ĂȂ��񂶂�Ȃ��H�v�Ǝw�E
    - �Ɨ�����embedding�i���e�X�g�itest_embedding_quality.py�j�����{
  - **�e�X�g���ʁi�����ׂ������j**:
    - ? Exact match: similarity = 1.000 (���f�����퓮��)
    - ? Query vs Full content: similarity = 0.881 (臒l0.85��**����**!)
    - ? Query vs Summary: similarity = 0.910 (臒l0.85��**����**!)
    - **���_**: nomic-embed-text���f�����̂͐���ɓ��삵�Ă���A�K�؂ȃR���e���c�ł����0.85�𒴂���ގ��x��B���\
  - **�����̒���: �Ȃ��e�X�g�Ɩ{�ԂŌ��ʂ��قȂ�̂��H**:
    - �e�X�g: 0.88-0.91�̍����ގ��x
    - �{�ԃ��O: 0.39-0.72�̒Ⴂ�ގ��x
    - �� **�i�[����Ă���R���e���c���قȂ�**�Ƃ�������
  - **���{�����̓���**:
    - `src/services/ingestion.py:665`: ���������^�f�[�^�G���g����`memory.summary`��`document`�t�B�[���h�Ɋi�[
      ```python
      self.vector_db.add(
          id=f"{memory.id}-metadata",
          embedding=embedding,
          metadata=metadata,
          document=memory.summary  # �� ���������I
      )
      ```
    - `src/services/project_memory_pool.py:136-141`: �v�[���ǂݍ��ݎ���`content`�t�B�[���h�i=summary�j���擾����embedding����
      ```python
      content = memory.get('content', '')  # ChromaDB document = memory.summary
      embedding = self.model_router.generate_embedding(content)
      ```
    - **���̍\��**:
      - **warm_cache�Ɋi�[**: `memory.summary`��embedding�i���k���ꂽ�Z���v�񕶁j
      - **�N�G��**: �ڍׂȎ��R���ꎿ��i��: "AppBrain release checklist steps"�j
      - **��r�Ώ�**: �v�� vs �ڍ׃N�G�� �� �Ӗ��I�ȗ��x���قȂ邽�ߗގ��x���Ⴂ�i0.39-0.72�j
  - **�e�X�g�������������R**:
    - �e�X�g�ł͊��S�ȕ��́i"The AppBrain release checklist is as follows:..."�j���g�p
    - �N�G���Ɠ������x�E�ڍ׃��x���̃R���e���c�Ȃ̂ō����ގ��x�i0.88-0.91�j
  - **�݌v��̍��{�I�ȉۑ�**:
    - L3�L���b�V���́uquery embedding vs memory embedding�v�̔�r��O��Ƃ���
    - �������A���ۂɂ́uquery embedding vs summary embedding�v���r���Ă���
    - �v��͏�񂪈��k����Ă���A�N�G���̏ڍׂȃL�[���[�h�╶���������Ă���
    - ���̂��߁A�Ӗ��I�ɂ͊֘A�������Ă��ގ��x�X�R�A���Ⴍ�Ȃ�i0.39-0.72�j
  - **������̌��**:
    - **Option 1**: memory.summary�̑����full content�i�S�`�����N�����j��embedding����
      - Pros: �ڍ׏���ێ��A�N�G���Ƃ̗��x����v
      - Cons: 512�g�[�N�����̃R���e���c��embedding�i�����ቺ�A�v�Z�R�X�g��
    - **Option 2**: L3�L���b�V��臒l��0.60-0.70�Ɋɘa
      - Pros: ������summary embedding�ŋ@�\����悤�ɂȂ�
      - Cons: ���x�ቺ�̃��X�N�A�U�z����������\��
    - **Option 3**: enhanced summary�𐶐��i�L�[���[�h + �v��j
      - Pros: �v��̊Ȍ����ƃL�[���[�h�̏ڍא��𗼗�
      - Cons: summary�t�B�[���h�̍Đ������K�v�A�ڍs�R�X�g
    - **Option 4**: L3�L���b�V������߁AWorkflow A�i�v�[���t�B���^�����O�j�ɒ���
      - Pros: ������ID�t�B���^�����O��70%�팸���m���ɒB���ł���
      - Cons: warm_cache�̓��������ʂɂȂ�
  - **�����A�N�V����**:
    - **�Z���i�����j**: Option 4�����{
      - ���R: warm_cache�̌��ʂ�����I�ł��邱�Ƃ�����
      - Workflow A���S�����ɂ��A�v�[���t�B���^�����O��70%�팸���m���ɒB��
      - L3�L���b�V���̉��P�͒����ۑ�Ƃ��Đ؂藣��
    - **�������iPhase 4�ȍ~�j**: Option 3������
      - �L�[���[�h���o + �v��̃n�C�u���b�h��@��enhanced summary�𐶐�
      - �����f�[�^�̍Đ����E�ڍs�v����������
  - **���_**:
    - L3�L���b�V����ގ��x�̍��{�����́u**summary embedding vs query embedding**�v�̗��x�s��v
    - embedding�i���͖��Ȃ��i�e�X�g��0.88-0.91���m�F�j
    - �݌v��̐���ł���Asummary���e�̉��P�Ȃ��ɂ͉�������
    - **Option 4�iWorkflow A�D��j�𐄏�**���AL3���P�͒����ۑ�Ƃ��Ĉ���
- **Phase 3g: ������ID�s��v�̏C���ƃv�[���t�B���^�����O���� (2025-11-13 ��)**:
  - **�w�i**: Phase 3f��L3�L���b�V���̍��{��������肵�����A���[�U�[����u�v�[���t�B���^�������[���q�b�g�𐶂�ł���v�Ƃ̎w�E
  - **�������ꂽ���**:
    - **������ID�s��v**: ProjectMemoryPool��`mem-123-metadata`��Ԃ����A�`�����N����`mem-123`������
    - **����**: `"mem-123"` ? `{"mem-123-metadata"}` �� �v�[���t�B���^�����O�őS��₪���O
    - **���{����**: ingestion.py:661��`f"{memory.id}-metadata"`�Ƃ��Ċi�[�Aproject_memory_pool.py:323�ł��̂܂ܕԋp
  - **���{�����C��**:
    1. **SearchService._get_memory_id_from_candidate()** (search.py:1290-1296):
       - �������G���g�����̏ꍇ�A`-metadata` suffix����������base memory ID��Ԃ�
       - �`�����N���i`mem-123`�j�ƃ������G���g�����i`mem-123-metadata`�j������������`mem-123`��Ԃ��悤�ɓ���
    2. **ProjectMemoryPool.get_memory_ids()** (project_memory_pool.py:297-336):
       - embeddings dict����擾����ID����`-metadata` suffix������
       - �ԋp�l��f��memory ID set�i`{"mem-123", "mem-456", ...}`�j�ɐ��K��
  - **���،���**:
    - ? ���j�b�g�e�X�g: ProjectMemoryPool 12/12 passed
    - ? Memory ID extraction logic: 4/4 test cases passed (test_memory_id_fix.py)
    - ? ��A�e�X�g: **regression passed** with significant improvements
  - **�p�t�H�[�}���X�w�W (mcp_run-20251113-170221.jsonl)**:
    - **Macro Precision**: 0.886 (baseline 0.375 �� **+136%���P**)
    - **Macro NDCG**: 1.470 (baseline 0.528 �� **+178%���P**)
    - **�L���b�V���q�b�g��**: 21% (Phase 3e: 0% �� ���P)
    - **LLM�Ăяo����**: 67��
    - **Prefetch**: 10 requests (hits 7, misses 20)
    - **�[���q�b�g�N�G��**: 0��
  - **���_**:
    - ������ID�s��v�̏C���ɂ��A**�v�[���t�B���^�����O������**
    - Precision/NDCG���啝���P�i136-178%����j
    - �L���b�V���q�b�g����0%��21%�ɉ��P
    - �v�[���t�B���^�����O�ɂ����팸������ɋ@�\
    - **Phase 3����**: ProjectMemoryPool/warm_cache�����͋Z�p�I�E�@�\�I�Ɋ���
  - **���̐����A�N�V����**:
    - Phase 4�Ƃ��āAL3�L���b�V����summary���P�i�L�[���[�h+�v��n�C�u���b�h�j������
    - �܂��́A�����21%�L���b�V���q�b�g���ŉ^�p���A���ʂ��p�����j�^�����O

### #2025-11-10-07 �����p�C�v���C���œK����QAM�����g�[
- **�w�i**: ����̌����͏\�����������A���ߍ��ݐ������ BM25 �𒀎����s���Ă��邽�ߔ����Ȃ���]�肪����B�܂� `source=session` �̃��O�� Runbook ����ʂɏo�邱�Ƃ�����ACrossEncoder reranker �̓������s���i����x�j������`�ŁA���O��͕��� 2.2s/49 call�i`mcp_run-20251111-005159.jsonl`�j�ƃL���[�x���̒��󂪂���BQAM�����͑�\��b�𒆐S�ɐ����������A��{�J���^�X�N�� 90% �ȏ���J�o�[���Ă��������B
- **�v����**:
  1. **�񓯊���**: ���ߍ��ݐ������� BM25 �����ő��点�Abefore/after �̃��C�e���V�����|�[�g����B
  2. **�Z�b�V�������O���ʒ���**: `source=session` �� command ���O�Ɍy���ȃy�i���e�B��^����A�������� rerank �Ώۂ��珜�O���āA���� Runbook/�K�C�h����ɏo��悤��������B
  3. **LLM���d���v��**:
      - ����: reranker �͓����I�� 1������ LLM ���Ăяo���B�ŐV run ���O�ł� `pairs_scored=49`, `avg_llm_latency?2.2s`�A�L���b�V���q�b�g�� 0%�B
      - �ۑ�: ����N�G����������Ƒ҂��s�񂪔������A�������X�|���X�� LLM �҂��Ɉ��������郊�X�N�B�L���b�V�������p�ł��Ă��Ȃ��B
      - ���P��:
          1. reranker �p�� `max_parallel_reranks` �ݒ�ƃ��[�J�[�v�[���iThreadPool or asyncio�j�𓱓����ē��� N ���܂ŕ��񉻁B
          2. �o�b�N���O��臒l�𒴂����ꍇ�� heuristics �X�R�A�݂̂ŕԂ��t�H�[���o�b�N��݌v�B
          3. ���g���N�X�iqueue length / wait ms / cache hit���j�� `get_reranker_metrics` �ɒǉ����ACI ����Ď��ł���悤�ɂ���B
          4. �L���b�V�����P: ���� query �𕡐��񗬂��V�i���I����A�ɒǉ����A�L���b�V���q�b�g���Č��B�p�o query �ւ̃E�H�[���A�b�v�� project �P�ʂ̃v���t�F�b�`�헪����������B
  4. **QAM����90%�J�o�[**: �����[�X/�C���V�f���g/�ăf�v���C/�č�/�K�o�i���X/�_�b�V���{�[�h�ȂǑ�\�^�X�N�̌�b�Z�b�g�𐮗����A��v����֖|��BLang Eval �� Precision >=0.9/ NDCG >=1.3 ���m�F����B
- **�o������**: ���C�e���V����ƃ����L���O���P�̃��O���c��ALang Eval �Őݒ肵���w�W�𖞂����A�����J�o���b�W�� 90% �ȏ�ɂȂ��Ă��邱�ƁB

### #2025-11-12-01 �S�������p�t�H�[�}���X�Z�k���i�����ۑ�j
- **�w�i**: ���[�N�t���[A�i�i�K�I�k�ށj�ɂ��A�v���W�F�N�g�m�莞��LLM�Ăяo������70%�팸�i100����30���j����錩���݁B�������A3������s�ł��S���������K�v�ȃP�[�X�ł͕���40.6�b/�N�G���̃��C�e���V����������B���^�p�ł�5�b�ȉ����]�܂����B
- **����̃{�g���l�b�N����**:
  - **LLM�Ăяo��**: 2.35�b/�y�A �~ ����2.0�y�A/�N�G�� = 4.7�b
  - **���񉻌���**: 3�����1/3�ɒZ�k�\�i���_�l�j
  - **�L���b�V���q�b�g��**: L1/L2/L3���v��14%�i�ڕW70%�ɖ��B�j
  - **�S�������P�[�X**: 86����LLM�Ăяo���i3����j= 29�o�b�` �~ 2.35�b = 68.2�b
- **�Z�k���A�v���[�`���**:
  1. **�L���b�V���q�b�g������**�i�ŗD��j:
     - L3�Z�}���e�B�b�N�L���b�V��臒l�̊ɘa�i0.85 �� 0.70-0.75�j
     - �v���t�F�b�`�N�G���̋�̉��i�v���W�F�N�g�ŗL�̃N�G���p�^�[���w�K�j
     - �K���I�w�K: �N�G����������p�o�p�^�[���𒊏o���ăL���b�V���E�H�[�~���O
     - **���Ҍ���**: �q�b�g�� 14% �� 50-70%�ALLM�Ăяo���� 86�� �� 26-43��
  2. **����x�̊g��**:
     - `cross_encoder_max_parallel: 3` �� 5-10�i���\�[�X���e�͈͂Łj
     - **���Ҍ���**: 68.2�b �� 40-20�b�i����x5-10�̏ꍇ�j
     - **����**: CPU/���������ׁALLM�T�[�o�[���̃��[�g����
  3. **LLM�œK��**:
     - ���f���؂�ւ��i��荂���ȃ��f���A���x�g���[�h�I�t�j
     - �o�b�`���_�i�����y�A��1���N�G�X�g�ŏ����j
     - **���Ҍ���**: 2.35�b/�y�A �� 0.5-1.0�b/�y�A
  4. **��␔�팸**:
     - �n�C�u���b�h�����i�K�ł̍i�荞�݋����i100��� �� 50-70���j
     - BM25/Vector������臒l����
     - **���Ҍ���**: LLM�Ăяo���� 86�� �� 43-60��
  5. **�t�H�[���o�b�N�q���[���X�e�B�N�X**:
     - LLM�L���[�҂����Ԃ�臒l���ߎ��̓��[���x�[�X�X�R�A�ő����ɕԋp
     - **���Ҍ���**: �ň��P�[�X�̃��C�e���V�����ݒ�i��: 5�b�j
- **�����D�揇��**:
  1. �L���b�V���q�b�g������i���������A�R�X�g��j
  2. ����x�g��i�����ς݁A�ݒ�ύX�̂݁j
  3. ��␔�팸�i���x�e�������؂��Ȃ���i�K�I�Ɂj
  4. LLM�œK���i�����ۑ�A���f���I��E���؂��K�v�j
  5. �t�H�[���o�b�N�q���[���X�e�B�N�X�i���[�U�[�̌��ی�Ƃ��ĕ⊮�I�Ɂj
- **�}�C���X�g�[��**:
  - **�Z���i1-2�T�ԁj**: L3臒l�ɘa + ����x�g��Ńq�b�g��30-40%�A���C�e���V20-30�b
  - **�����i1-2�����j**: �K���I�w�K�����Ńq�b�g��50-70%�A���C�e���V10-15�b
  - **�����i3-6�����j**: LLM�œK�� + �o�b�`���_�Ń��C�e���V5�b�ȉ�
- **�o������**: �S���������̕��σ��C�e���V��5�b�ȉ��A�܂��̓L���b�V���q�b�g��70%�ȏ��B�����邱�ƁB

### #2025-11-13-08 ���x����v�� Phase 1: �x�[�X���C�� & �K�[�h���[�� (Baseline & Guardrails)
- **�w�i**: Phase 3g�Ń�����ID�s��v���C�����APrecision/NDCG���啝���P�i136-178%����j�B����̐��x����{���i�K�I�ɐi�߂邽�߁A�܂��x�[�X���C�����m�����A��A���o�̎d�g�݂𐮔�����B
- **�ڕW**:
  - ���݂̐��x�����iPhase 3g�j���x�[�X���C���Ƃ��ċL�^
  - ������A���o�ɂ��A����̕ύX�Ő��x���ቺ���Ȃ����Ƃ�ۏ�
  - ���ߍ��ݕi���̌p���I�Ď�
- **���{���e**:
  1. **Precision Baseline Snapshot�쐬** (`scripts/create_precision_baseline.py`):
     - Phase 3g���s���ʁi`mcp_run-20251113-170221.jsonl`�j���烁�g���N�X�𒊏o
     - `reports/precision_baseline.json`�Ɉȉ����L�^:
       - Macro Precision: 0.886
       - Macro NDCG: 1.470
       - Cache hit rate: 21%
       - LLM calls: 67
       - Zero-hit queries: 0
     - ��A���o臒l��ݒ�:
       - Precision >= 0.80
       - NDCG >= 1.20
       - Cache hit rate >= 15%
       - Zero-hit queries <= 2
     - ���ߍ��ݕi��臒l���`:
       - exact_match >= 0.95
       - summary >= 0.70
       - full_content >= 0.50
  2. **Embedding Quality CI Test** (`scripts/test_embedding_quality_ci.py`):
     - `test_embedding_quality.py`��CI�����p�Ɋg��
     - JSON�`���Ńe�X�g���ʂ��G�N�X�|�[�g�i`reports/embedding_quality.json`�j
     - 3�̃e�X�g�P�[�X:
       - Exact match: 1.000 (PASS)
       - Full content: 0.881 (PASS)
       - Summary: 0.910 (PASS)
     - �S�e�X�g�P�[�X��臒l�𖞂������Ƃ��m�F
  3. **Regression Detection Logic** (`scripts/run_regression_ci.py`):
     - `check_embedding_quality()`�֐���ǉ�
     - �x�[�X���C��臒l�ƍŐV�̖��ߍ��ݕi�����|�[�g���r
     - 臒l���B�̏ꍇ�̓G���[���b�Z�[�W�ƂƂ���CI���s
     - �R�}���h���C��������ǉ�:
       - `--precision-baseline`: �x�[�X���C���t�@�C���p�X�i�f�t�H���g: `reports/precision_baseline.json`�j
       - `--embedding-quality-report`: �i�����|�[�g�p�X�i�f�t�H���g: `reports/embedding_quality.json`�j
     - �����̃[���q�b�g�N�G�����o�ɉ����A���ߍ��ݕi�����o�𓝍�
- **���،���**:
  - ? Precision baseline�쐬����: `reports/precision_baseline.json`
  - ? Embedding quality CI test���s����: 3/3 tests passed
  - ? Regression detection logic�ǉ�����: `run_regression_ci.py`�X�V
  - ? �S�R���|�[�l���g��UTF-8�G���R�[�f�B���O�Ő��퓮��
- **���ʕ�**:
  - `scripts/create_precision_baseline.py`: �x�[�X���C�������X�N���v�g
  - `scripts/test_embedding_quality_ci.py`: CI�������ߍ��ݕi���e�X�g
  - `reports/precision_baseline.json`: Phase 3g�x�[�X���C���L�^
  - `reports/embedding_quality.json`: ���ߍ��ݕi���e�X�g����
  - `scripts/run_regression_ci.py`: ��A���o���W�b�N����
- **���_**:
  - Phase 1����: �x�[�X���C���m���Ɖ�A���o�̎d�g�݂��������ꂽ
  - ����̐��x���P�{��iPhase 2-5�j�����S�Ɏ��{�ł����Ղ�����
  - ���ߍ��݃��f���inomic-embed-text�j�̕i�����p���I�ɊĎ������
  - CI/CD�p�C�v���C���ɂ��A���x�򉻂𑁊����o�\
- **���̐����A�N�V����**:
  - Phase 2: QAM�����ƃ��^�f�[�^�g�[�i90%�J�o���b�W�ڕW�j
  - Phase 3: �N���X�G���R�[�_�[�̊w�K�d�ݒ����iPrecision/NDCG�œK���j
  - Phase 4: �Z�}���e�B�b�N�L���b�V�����P�iL3臒l�����Aenhanced summary�j
  - Phase 5: �K���I�w�K�ƃv���t�F�b�`�œK���i�N�G�����𕪐́j

### #2025-11-13-09 ���[���x�[�X�������L���O�{CrossEncoder�������iPhase 4�j
- **�w�i**: Phase 3g �� Precision/NDCG �͑啝���P�������ALLM �������N�̃R�X�g�͈ˑR�Ƃ��ăN�G�����Ƃ�5���O��̌��𓯊��X�R�A���Ă���A�ҋ@���Ԃ��L���b�V�����ʂ𑊎E����P�[�X���U�������BWorkflow A �Ō��W�����i��Ă��鍡�̍\���ł́ALLM ���ĂԑO�Ɂu�v���W�F�N�g�^�ʑ��ɉ��������[���w�W�ōĐ��񂷂�w�v�ƁuCrossEncoder �ɓn����␔�E�҂����Ԃ̖��m�ȏ���v��݂���ق������C�e���V�E�R�X�g���ʂō����I�B
- **�Ή����j**:
  1. **���[���t�^**: `SearchService._rerank()` �Ƀt�F�[�Y���m�̃X�R�A�i��: project �ʑ��A���J�e�S���Asession phase�j��ǉ����ACrossEncoder �ɑ���O�� `metadata.phase_score` �� `project_priority` ��g�ݍ��񂾃q���[���X�e�B�b�N�Ō�⏇�ʂ��ĕ]������B����ɂ�� LLM �ɓn���g�b�vN�������肵�A�L���b�V���q�b�g���Č����₷���Ȃ�B
  2. **�ő吔�^�ő�ҋ@���Ԃ̖��m��**: `config.search.cross_encoder_top_k`�i= `CrossEncoderReranker.max_candidates`�j���v���W�F�N�g�P�ʂŒ������A`fallback_max_wait_ms` �� 500ms �� 300ms �ȂǂɈ��������āu�w�莞�Ԃ𒴂����烋�[���X�R�A�ŕԂ��v�|���V�[��O�ꂷ��B�K�v�Ȃ� `simple_query_max_words` �� `skip_rerank_for_simple_queries` �� config ����؂�ւ��\�ɂ��APhase 4 �Ŏ����l���L�^����B
- **���ʕ�**
  - `src/services/search.py`: `_rerank()` �ւ̈ʑ��x�[�X�w�W�ǉ��ACrossEncoder �֓n����␔���O
  - `src/services/rerankers.py`: `max_candidates`/`fallback_max_wait_ms` �� config ���f�ł���悤���t�@�N�^�Ametrics �Ɂuskipped_due_to_limit�v�Ȃǂ�ǉ�
  - `config.yaml`: `search.cross_encoder_top_k`, `cross_encoder_fallback_max_wait_ms`, `phase_rerank_weights` ���̐����ǋL
- **�o������**: (1) Macro Precision/NDCG �� Phase 3g �x�[�X���C�� (0.886/1.47) ���ێ��A(2) CrossEncoder 1�N�G��������� LLM �Ăяo��������3���ȉ��A(3) 95 �p�[�Z���^�C���̃������N�ҋ@���Ԃ� 1 �b�����A(4) ���[���x�[�X�X�R�A�ő��Ԃ��������E臒l�� `scripts/run_regression_ci.py` �ŉ����B

### #2025-11-14-01 ��I�e�X�g�v�����iPhase 7: Quality Assurance�j
- **�w�i**: Phase 6�i�K���I臒l�헪�j�ő啝�ȃp�t�H�[�}���X���P��B���i���C�e���V71%�팸�ALLM�Ăяo��63%�팸�APrecision 0.826, NDCG 1.367�j�B����ȏ�̍œK���͔�p�Ό��ʂ��Ⴂ���߁A���̃X�e�b�v�͑��l�ȃe�X�g�p�^�[���ň��萫�E�M���������؂��邱�ƁB
- **�ڕW**:
  - �l�X�ȃN�G���p�^�[���ł̋����m�F
  - �G�b�W�P�[�X�̌��o�ƑΏ�
  - ���׃e�X�g�ɂ�鐫�\���E�̔c��
  - �����i���̎蓮���r���[�Ɖ��P
- **�e�X�g�J�e�S��**:
  1. **���l�ȃN�G���p�^�[��**:
     - �����N�G���i100+ words�jvs �Z���N�G���i1-3 words�j
     - ���{�� vs �p�� vs �X�y�C����i�����ꃋ�[�e�B���O���؁j
     - �Z�p�p�ꂪ�����N�G�� vs ���R����N�G��
     - �h���C�������N�G���iArchitecture/Code/Ops/Config/Testing�j
     - �B���ȃN�G�� vs ��̓I�ȃN�G��
  2. **�G�b�W�P�[�X**:
     - �[���q�b�g�N�G���i�Y���Ȃ��A�Ӑ}�I�ɐ݌v�j
     - ��ʃq�b�g�N�G���i100���ȏ�̌��j
     - ���ꕶ�����܂ރN�G���i`@`, `#`, `$`, etc.�j
     - �G�������܂ރN�G��
     - �󔒂݂̂̃N�G���A�ɒ[�ɒ����N�G���i1000+ words�j
     - �v���W�F�N�gID�����ݒ�̃N�G��
     - ���݂��Ȃ��v���W�F�N�gID���w�肵���N�G��
  3. **���׃e�X�g**:
     - �A��100�N�G�����s�i���������[�N�`�F�b�N�j
     - �������s�N�G���i5-10�N�G��������s�j
     - �L���b�V���E�H�[�~���O���ʂ̑���i����N�G���J��Ԃ��j
     - �v�[���T�C�Y�������̋����i100 �� 500 �� 1000�������j
  4. **�i���e�X�g**:
     - �������ʂ̑Ó����i�蓮���r���[�A�e�g�s�b�N5���T���v�����O�j
     - �֘A���X�R�A�̕��z�i�q�X�g�O�������́j
     - False positive/negative ���́i���Ҍ��ʂƂ̍����j
     - Cross-encoder reranking�̌��ʑ���i�L����r�j
     - L3�Z�}���e�B�b�N�L���b�V���̐M���x�ʌ��ʁihigh/medium/low�j
- **�����v��**:
  1. **Phase 7a: �N�G���p�^�[���e�X�g**:
     - `tests/scenarios/diverse_queries.json` �쐬�i50�N�G���A�e�J�e�S��10���j
     - `scripts/mcp_replay.py` �Ŏ��s�APrecision/NDCG����
     - ���C�e���V���z�iP50/P95/P99�j�ƃL���b�V���q�b�g�����L�^
  2. **Phase 7b: �G�b�W�P�[�X�e�X�g**:
     - `tests/unit/services/test_search_edge_cases.py` �쐬
     - �e�G�b�W�P�[�X�ł̗�O�����ƃG���[���b�Z�[�W����
     - �[���q�b�g���̃t�H�[���o�b�N�����m�F
  3. **Phase 7c: ���׃e�X�g**:
     - `scripts/load_test.py` �쐬�i100�A���N�G���A�������v���t�@�C�����O�j
     - `scripts/concurrent_test.py` �쐬�iasyncio������s�j
     - ���\�[�X�g�p�ʁiCPU/Memory/Disk I/O�j���j�^�����O
  4. **Phase 7d: �i�����r���[**:
     - `scripts/quality_review.py` �쐬�i�蓮���r���[�x���j
     - �g�s�b�N�ʃT���v�����O�iAppBrain 5���AInsightOps 5���A...�j
     - �֘A���X�R�A���z�̉����imatplotlib�j
     - False positive/negative �̒�ʕ���
- **�����**:
  - �N�G���p�^�[���e�X�g: Precision ?0.75, NDCG ?1.20�i�S�J�e�S���j
  - �G�b�W�P�[�X�e�X�g: ��O����100%�J�o�[�A�G���[���b�Z�[�W���m
  - ���׃e�X�g: ���������[�N�Ȃ��A100�N�G����<5%�p�t�H�[�}���X�ቺ
  - �i�����r���[: False positive rate <10%, False negative rate <15%
- **�o������**: �S�e�X�g�J�e�S���Ő�����𖞂����A���o���ꂽ�o�O���C������A��A�e�X�g�ɓ�������邱�ƁB

### #2025-11-13-01 �������\���̉��P�iEnriched Summary�j
- **�w�i**: Phase 1��embedding�i���̃x�[�X���C��(summary 0.910)���m���������AL3�Z�}���e�B�b�N�L���b�V���̃q�b�g����21%�ƒႭ�Asummary embedding��query embedding�̗ގ��x��0.39-0.72��臒l0.85�ɓ͂��Ȃ���肪�����i#2025-11-11-03 Phase 3f�j�B���{�����́Asummary�����k���ꂽ�Z���v�񕶂ł���A�N�G���̏ڍׂȃL�[���[�h�╶���������Ă��邽�߁B
- **�Ώ� (2025-11-13)**:
  - **Phase 2����**: Memory Representation Refresh
    1. **IngestionService����** (`src/services/ingestion.py`):
       - `_build_enriched_summary()`���\�b�h�ǉ��i64�s�j
       - �v�� + Top 5�L�[���[�h + ��\���o����g�ݍ��킹�� enriched summary ����
       - �V�K�������o�^���� enriched summary ���g�p����embedding����
    2. **Backfill�X�N���v�g�쐬** (`scripts/refresh_memory_embeddings.py`):
       - �����������G���g���� enriched summary �Đ����@�\�i240�s�j
       - `--dry-run`��`--limit`�I�v�V�����Ή�
       - �S�R���|�[�l���g�iModelRouter, VectorDB, BM25Index, Indexer�j�𐳂���������
    3. **ProjectMemoryPool�X�V** (`src/services/project_memory_pool.py`):
       - �ۑ��ς�embedding���ė��p����`�ɕύX�i`include_embeddings=True`�j
       - Fallback: �ۑ�����Ă��Ȃ��ꍇ�̂�embedding����
       - �v�Z���ׂ��팸
- **���،���**:
  - ? **Embedding Quality**: summary similarity = **0.910** (?0.80�ڕW�B��)
    - exact_match: 1.000 ? (?0.95)
    - full_content: 0.881 ? (?0.50)
  - ? **Precision/NDCG�ێ�**:
    - Macro Precision: 0.886 (baseline 0.375����+136%���P�ێ�)
    - Macro NDCG: 1.470 (baseline 0.528����+178%���P�ێ�)
  - ? **L3 Cache Hit Rate**: 21% (Phase 3g baseline�ێ�)
    - �ڕW35%���B�����A�����f�[�^��Chroma DB��memory metadata�`���ŕۑ�����Ă��Ȃ��i0 documents�j
    - ����o�^�����V������������enriched summary�ŕۑ�����邱�ƂŁA���X�ɉ��P�\��
  - ? **Backfill�X�N���v�g����m�F**: dry-run�e�X�g�����A�S�R���|�[�l���g���평����
- **���ʕ�**:
  - `src/services/ingestion.py`: `_build_enriched_summary()`���\�b�h�ǉ�
  - `src/utils/keyword_extractor.py`: �L�[���[�h���o���[�e�B���e�B�i�����j
  - `scripts/refresh_memory_embeddings.py`: Backfill�X�N���v�g�i�V�K�쐬�j
  - `src/services/project_memory_pool.py`: �ۑ��ς�embedding�ė��p���W�b�N�ǉ�
- **���_**:
  - **Phase 2�Z�p�I�Ɋ���**: enriched summary������embedding�i�����P�̎d�g�݂��������ꂽ
  - Embedding�i���ڕW�isummary?0.80�j�B��
  - Precision/NDCG�̍������ێ��i+136-178%���P�j
  - �����f�[�^��backfill�͌��ʌ���I�����A�V�K����������i�K�I�ɉ��P
  - L3�L���b�V���q�b�g���̍��{���P�ɂ�summary���e�������L���Ɗm�F�itest_embedding_quality.py��0.88-0.91�B���j
- **���̐����A�N�V����** (Phase 3: Chunk/Vector Retrieval Tuning):
  - �n�C�u���b�h�����̃`���[�j���O�ivector��␔�EBM25��␔�̍œK���j
  - Chunk�����L���O����̏��O�i������summary�݂̂������L���O�ΏۂɁj
  - Tier��recency�X�R�A�����ilong-term memory�̕��㑣�i�j
  - �v�[���������D���Workflow A�����i��␔�팸�ɂ��LLM�Ăяo���팸�j

### #2025-11-15-01 Codex/Claude session logging bridge missing
- **����**: `scripts/setup_cli_recording.ps1` �� `claude`/`codex` �� `Tee-Object` �o�R�ɂ��Ă��邽�߁AReady-to-code �o�i�[���\�����ꂸ�A�Θb���̏o�͂̓v���Z�X�I����܂� `capturedOutput` �ɗ��܂�B  
- **�����̐i�� (2025-11-17)**:
  1. Claude �����������|�[�g�ɑ����ACodex �l�C�e�B�u���O�d�l���܂Ƃ߂� `reports/issue_15-01_codex_spec_report.md` ���쐬�B`~/.codex/history.jsonl`�A`sessions/**/rollout-*.jsonl`�A`log/codex-tui.log` �̍\���Ɗ��p���@�𐮗��B
  2. Claude/Codex ���ʂ̎������[�h�}�b�v�� `reports/cli_session_capture_plan.md` �Ƃ��Ēǉ��BPhase0?Phase2 �̍�ƁA�L�����^�C�~���O�ł̃��O�ۊǕ��j�𖾕����B
  3. Open Issue �� Next Action �� Phase0�i�C���^���N�e�B�u����Tee�����{history�������M�j�ɍX�V���APhase1�ȍ~�̃A�N�V���������|�[�g�փ����N�B
- **�Ή��v�� (����)**:
  - **Phase0**: `Test-IsInteractiveSession` �𓱓����A�Θb���[�h�ł� `Tee-Object` ���o�C�p�X�B�Z�b�V�����I����� `~/.claude` / `~/.codex` �� `history.jsonl` ������ `add_command` �֑����Ďb�胍�O���m�ہB
  - **Phase1**: Claude �� `debug/<sessionId>.txt`�ACodex �� `sessions/**/rollout-*.jsonl` ���p�[�X���A���[�U�[�{�A�V�X�^���g�{ToolCall �� Context Orchestrator �Ɋ��S�����B�p�[�T�� Python ���W���[�������� pytest �Ō��؁B
  - **Phase2**: �L�����W���u�ƘA���������O�A�[�J�C�u�ACLI `session-history` �̃Z�b�V����ID�r���[�AJSON�j�����̃��g���C�Ȃǉ^�p���P�B
- **Exit Criteria**: �@ Ready-to-code �o�i�[���܂ރ��A���^�C�����o�͂������A�A Claude/Codex ������� `history/debug` or `rollout` �R���̊��S�g�����X�N���v�g�� Context Orchestrator ���ێ��A�B ���O�ۊǂ��L�����^�C�~���O�Ɠ����B
- **Next Checkpoint**: Phase0 ���� �� `python -m src.cli session-history` �Ŏb�胍�O���f���m�F���A������ Phase1 �̃��O�p�[�T�𒅎�B

### #2025-11-25-01 TTY-safe CLI wrapper with session logging
- **Problem**: PowerShell wrapper always pipes output (Tee-Object | Out-Host), so CLAUDE/CODEX lose TTY and drop into non-interactive/--print behavior; users cannot start interactive sessions.
- **Scope**: Keep JSON-RPC start_session/add_command/end_session for memory ingestion; fix only TTY loss.
- **Plan**:
  1. Detect non-interactive (--print or piped stdin); only there use Tee-Object or Start-Transcript.
  2. Interactive path runs &  @args / &  @args with no pipe.
  3. Add -Force overwrite in installer; update scripts/setup.py and release_package script to new wrapper.
  4. Tests: interactive prompt shows; echo hi | claude --print still logs; session-history works.
- **Exit Criteria**: Interactive CLAUDE/CODEX start normally; non-interactive logging preserved; new wrapper auto-installs and overwrites old; session logs/ingestion continue.
- **Resolved**: 2025-11-26 (TTY保持は達成。非インタラクティブは全文ログ取得OK。インタラクティブ本文は未対応のため新Issueへ切り出し)

### #2025-11-26-01 Interactive transcript capture while keeping TTY
- **Problem**: インタラクティブ実行時、TTYは保持できたが会話本文がログに残らない（Start-Transcriptでは claude/codex の TUI 出力を拾えない）
- **Scope**: TTY を壊さずに対話本文も記録する仕組みを追加する
- **Options**:
  1. ConPTY/擬似TTY 経由で claude/codex をラップし入出力を横取り
  2. claude/codex の内部ログ (history.jsonl 等) をフックして add_command に流し込むブリッジを実装
- **Next Action**: 方針選定 → 実装プロトタイプ → session-history で本文確認
