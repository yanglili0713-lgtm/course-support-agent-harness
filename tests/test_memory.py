from agent_harness.memory import MemoryStore
from agent_harness.schemas import MemoryLayer


def test_memory_consolidates_episodic_grading_into_stable_layers():
    store = MemoryStore()
    store.add(MemoryLayer.EPISODIC, "weak answer", kind="grading", score=70)

    promoted = store.consolidate()

    assert any(item.layer == MemoryLayer.SEMANTIC for item in promoted)
    assert any(item.layer == MemoryLayer.PROCEDURAL for item in promoted)

