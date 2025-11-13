#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test memory ID matching fix
"""

import sys
sys.path.insert(0, 'src')

def test_memory_id_extraction():
    """Test that memory ID extraction handles -metadata suffix correctly"""
    from src.services.search import SearchService

    # We don't need full initialization, just test the method
    search_service = SearchService.__new__(SearchService)

    # Test case 1: Chunk candidate (has metadata.memory_id)
    chunk_candidate = {
        'id': 'chunk-abc-1',
        'metadata': {
            'memory_id': 'mem-123',
            'chunk_index': 0
        }
    }

    result1 = search_service._get_memory_id_from_candidate(chunk_candidate)
    assert result1 == 'mem-123', f"Expected 'mem-123', got '{result1}'"
    print(f"[PASS] Chunk candidate: extracted '{result1}'")

    # Test case 2: Memory entry candidate (has is_memory_entry=True, ID with -metadata suffix)
    memory_candidate = {
        'id': 'mem-123-metadata',
        'metadata': {
            'is_memory_entry': True,
            'schema_type': 'Incident'
        }
    }

    result2 = search_service._get_memory_id_from_candidate(memory_candidate)
    assert result2 == 'mem-123', f"Expected 'mem-123', got '{result2}'"
    print(f"[PASS] Memory entry candidate: extracted '{result2}' (stripped -metadata)")

    # Test case 3: Memory entry without -metadata suffix (edge case)
    memory_candidate_no_suffix = {
        'id': 'mem-456',
        'metadata': {
            'is_memory_entry': True
        }
    }

    result3 = search_service._get_memory_id_from_candidate(memory_candidate_no_suffix)
    assert result3 == 'mem-456', f"Expected 'mem-456', got '{result3}'"
    print(f"[PASS] Memory entry without suffix: extracted '{result3}'")

    # Test case 4: Invalid candidate (no memory_id, not a memory entry)
    invalid_candidate = {
        'id': 'unknown',
        'metadata': {}
    }

    result4 = search_service._get_memory_id_from_candidate(invalid_candidate)
    assert result4 == '', f"Expected empty string, got '{result4}'"
    print(f"[PASS] Invalid candidate: returned empty string")

    print("\n" + "=" * 80)
    print("All tests passed! Memory ID extraction handles -metadata suffix correctly.")
    print("=" * 80)

def test_project_memory_pool_ids():
    """Test that ProjectMemoryPool.get_memory_ids() strips -metadata suffix"""
    from src.services.project_memory_pool import ProjectMemoryPool

    # Create a minimal instance
    pool = ProjectMemoryPool.__new__(ProjectMemoryPool)
    pool._pools = {}

    # Simulate a loaded pool with -metadata IDs
    pool._pools['proj-123'] = {
        'project_id': 'proj-123',
        'loaded_at': 0.0,
        'memory_count': 3,
        'embeddings': {
            'mem-abc-metadata': [0.1, 0.2],
            'mem-def-metadata': [0.3, 0.4],
            'mem-ghi-metadata': [0.5, 0.6]
        },
        'metadata': {}
    }

    memory_ids = pool.get_memory_ids('proj-123')

    expected = {'mem-abc', 'mem-def', 'mem-ghi'}
    assert memory_ids == expected, f"Expected {expected}, got {memory_ids}"
    print(f"[PASS] ProjectMemoryPool.get_memory_ids() returned: {memory_ids}")
    print(f"       (stripped -metadata suffix from all IDs)")

    print("\n" + "=" * 80)
    print("ProjectMemoryPool test passed!")
    print("=" * 80)

if __name__ == "__main__":
    print("=" * 80)
    print("TESTING MEMORY ID MATCHING FIX")
    print("=" * 80)
    print()

    test_memory_id_extraction()
    print()
    test_project_memory_pool_ids()

    print("\n" + "=" * 80)
    print("SUCCESS: All memory ID matching tests passed!")
    print("=" * 80)
