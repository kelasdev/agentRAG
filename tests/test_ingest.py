from pathlib import Path
from uuid import UUID

from agentrag.ingest import ingest_paths
from agentrag.providers.embeddings import EmbeddingProvider


class FakeStore:
    def __init__(self):
        self.collection_ready = False
        self.upserted = []
        self.deleted_ids = []
        self.ids_by_source = {}

    def ensure_collection(self):
        self.collection_ready = True

    def list_point_ids_by_source_id(self, source_id):
        return set(self.ids_by_source.get(source_id, set()))

    def upsert(self, nodes):
        self.upserted.extend(nodes)
        for n in nodes:
            src = n.payload.source_id
            self.ids_by_source.setdefault(src, set()).add(n.id)

    def delete_by_ids(self, ids):
        self.deleted_ids.extend(ids)
        stale = set(ids)
        for _, id_set in self.ids_by_source.items():
            id_set.difference_update(stale)


def test_ingest_generates_uuid_ids(tmp_path: Path):
    f = tmp_path / "a.md"
    f.write_text("hello world\n\nsecond para", encoding="utf-8")
    store = FakeStore()
    result = ingest_paths(
        paths=[f],
        store=store,  # type: ignore[arg-type]
        embedder=EmbeddingProvider(dimensions=8),
    )

    assert result.nodes_created > 0
    assert result.skipped == 0
    assert store.collection_ready is True
    for node in store.upserted:
        assert str(UUID(node.id)) == node.id
        assert len(node.vector) == 8


def test_ingest_delta_sync_skips_unchanged_and_deletes_stale(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_text("alpha\n\nbeta", encoding="utf-8")

    store = FakeStore()
    embedder = EmbeddingProvider(dimensions=8)

    result_1 = ingest_paths(
        paths=[f],
        store=store,  # type: ignore[arg-type]
        embedder=embedder,
    )
    assert result_1.nodes_created > 0
    assert result_1.skipped == 0

    before_upsert_count = len(store.upserted)
    result_2 = ingest_paths(
        paths=[f],
        store=store,  # type: ignore[arg-type]
        embedder=embedder,
    )
    assert result_2.nodes_created == 0
    assert result_2.new_chunks == 0
    assert result_2.unchanged_chunks > 0
    assert result_2.skipped == 0
    assert len(store.upserted) == before_upsert_count

    f.write_text("alpha\n\ngamma", encoding="utf-8")
    result_3 = ingest_paths(
        paths=[f],
        store=store,  # type: ignore[arg-type]
        embedder=embedder,
    )
    assert result_3.nodes_created > 0
    assert result_3.new_chunks > 0
    assert result_3.stale_deleted > 0
    assert result_3.skipped == 0
    assert len(store.deleted_ids) > 0


def test_ingest_dry_run_no_write(tmp_path: Path):
    f = tmp_path / "dry.txt"
    f.write_text("one\n\ntwo", encoding="utf-8")

    store = FakeStore()
    result = ingest_paths(
        paths=[f],
        store=store,  # type: ignore[arg-type]
        embedder=EmbeddingProvider(dimensions=8),
        dry_run=True,
    )

    assert result.new_chunks > 0
    assert result.nodes_created == 0
    assert store.upserted == []
    assert store.deleted_ids == []
