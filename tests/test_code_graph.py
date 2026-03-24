from __future__ import annotations


from dataclasses import dataclass


from agentrag.qdrant_store import QdrantStore


@dataclass
class DummyPoint:
    id: str
    payload: dict


def test_qdrant_store_find_definitions_builds_filter(monkeypatch):
    store = QdrantStore(
        url="http://localhost:6333",
        api_key="",
        collection_name="test",
        vector_size=8,
    )

    captured = {}

    def fake_scroll(**kwargs):
        captured.update(kwargs)
        return ([DummyPoint(id="1", payload={"ok": True})], None)

    monkeypatch.setattr(store.client, "scroll", fake_scroll)

    points = store.find_definitions(
        symbol_name="foo",
        language="python",
        access_level="internal",
        limit=10,
    )

    assert len(points) == 1
    flt = captured.get("scroll_filter")
    assert flt is not None
    must = list(getattr(flt, "must", []) or [])
    keys = [c.key for c in must]
    assert "node_type" in keys
    assert "code_metadata.symbol_name" in keys
    assert "code_metadata.language" in keys
    assert "access_level" in keys


def test_qdrant_store_find_callers_builds_filter(monkeypatch):
    store = QdrantStore(
        url="http://localhost:6333",
        api_key="",
        collection_name="test",
        vector_size=8,
    )

    captured = {}

    def fake_scroll(**kwargs):
        captured.update(kwargs)
        return ([DummyPoint(id="1", payload={"ok": True})], None)

    monkeypatch.setattr(store.client, "scroll", fake_scroll)

    points = store.find_callers(
        callee_symbol_name="bar",
        language=None,
        access_level=None,
        limit=10,
    )

    assert len(points) == 1
    flt = captured.get("scroll_filter")
    assert flt is not None
    must = list(getattr(flt, "must", []) or [])
    keys = [c.key for c in must]
    assert "node_type" in keys
    assert "code_metadata.calls" in keys


def test_qdrant_store_ensure_payload_indexes_creates_expected_fields(monkeypatch):
    store = QdrantStore(
        url="http://localhost:6333",
        api_key="",
        collection_name="test",
        vector_size=8,
    )

    created: list[str] = []

    def fake_create_payload_index(*, collection_name: str, field_name: str, field_schema: str | None = None, **_):
        created.append(field_name)

    monkeypatch.setattr(store.client, "create_payload_index", fake_create_payload_index)

    store.ensure_payload_indexes()

    # Order is not important, but these fields should be attempted.
    for field in [
        "source_id",
        "node_type",
        "access_level",
        "code_metadata.language",
        "code_metadata.symbol_name",
        "code_metadata.calls",
    ]:
        assert field in created

