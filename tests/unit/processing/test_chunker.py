import importlib.util
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

CHUNKER_PATH = ROOT_DIR / "src" / "processing" / "chunker.py"
spec = importlib.util.spec_from_file_location("chunker_module", CHUNKER_PATH)
chunker_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(chunker_module)
Chunker = chunker_module.Chunker


class TestChunkerMetadata:
    def test_chunk_assigns_memory_and_index(self):
        chunker = Chunker(max_tokens=50)  # Lower token limit to force splitting
        # Generate longer text that will exceed 50 tokens
        text = "# H1\n\n" + " ".join(["Paragraph one with more content."] * 10) + "\n\n# H2\n\n" + " ".join(["Paragraph two with more content."] * 10)
        memory_id = "mem-test"

        chunks = chunker.chunk(text=text, memory_id=memory_id)

        assert len(chunks) >= 2
        for index, chunk in enumerate(chunks):
            assert chunk.memory_id == memory_id
            assert chunk.metadata["memory_id"] == memory_id
            assert chunk.metadata["chunk_index"] == index
            assert chunk.id == f"{memory_id}-chunk-{index}"

    def test_chunk_conversation_sets_metadata_defaults(self):
        chunker = Chunker(max_tokens=1000)
        memory_id = "mem-convo"

        chunks = chunker.chunk_conversation(
            user_message="What is the status?",
            assistant_message="All systems nominal.",
            memory_id=memory_id,
        )

        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.metadata["memory_id"] == memory_id
        assert chunk.metadata["chunk_index"] == 0

    def test_chunk_preserves_original_metadata(self):
        chunker = Chunker(max_tokens=1000)
        metadata = {"source": "journal"}
        memory_id = "mem-meta"

        chunks = chunker.chunk(
            text="Simple paragraph for testing.",
            memory_id=memory_id,
            metadata=metadata,
        )

        assert metadata == {"source": "journal"}
        for chunk in chunks:
            assert chunk.metadata["memory_id"] == memory_id
            assert chunk.metadata["chunk_index"] == 0
            assert chunk.metadata["source"] == "journal"
