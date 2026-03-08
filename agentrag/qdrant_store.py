from __future__ import annotations

from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from agentrag.models import VectorNode


class QdrantStore:
    def __init__(self, url: str, api_key: str, collection_name: str, vector_size: int) -> None:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        is_local = host in {"localhost", "127.0.0.1", "::1"}
        resolved_api_key = None if is_local else (api_key or None)
        self.client = QdrantClient(url=url, api_key=resolved_api_key)
        self.collection_name = collection_name
        self.vector_size = vector_size

    def ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        names = {c.name for c in collections}
        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
        self._ensure_payload_indexes()

    def _ensure_payload_indexes(self) -> None:
        # Improves delta re-ingest lookup by source_id filtering.
        try:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="source_id",
                field_schema="keyword",
            )
        except TypeError:
            # Backward compatibility for older clients that infer schema.
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="source_id",
                )
            except Exception:
                pass
        except Exception:
            pass

    def health_check(self) -> bool:
        try:
            _ = self.client.get_collections()
            return True
        except Exception:
            return False

    def count(self) -> Any:
        """Get the count of points in the collection."""
        return self.client.count(collection_name=self.collection_name, exact=False)

    def upsert(self, nodes: list[VectorNode]) -> None:
        points = [
            PointStruct(id=n.id, vector=n.vector, payload=n.payload.model_dump(mode="json"))
            for n in nodes
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def list_point_ids_by_source_id(self, source_id: str) -> set[str]:
        query_filter = Filter(
            must=[FieldCondition(key="source_id", match=MatchValue(value=source_id))]
        )
        ids: set[str] = set()
        offset = None

        while True:
            points, next_page = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=256,
                with_payload=False,
                with_vectors=False,
                offset=offset,
            )
            for point in points:
                ids.add(str(point.id))
            if next_page is None:
                break
            offset = next_page

        return ids

    def delete_by_ids(self, ids: list[str]) -> None:
        if not ids:
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=ids),
            wait=True,
        )

    def search(
        self,
        query_vector: list[float],
        limit: int = 3,
        node_type: str | None = None,
        language: str | None = None,
        symbol_name: str | None = None,
        access_level: str | None = None,
    ) -> list[ScoredPoint]:
        conditions: list[FieldCondition] = []
        if node_type:
            conditions.append(FieldCondition(key="node_type", match=MatchValue(value=node_type)))
        if language:
            conditions.append(
                FieldCondition(key="code_metadata.language", match=MatchValue(value=language))
            )
        if symbol_name:
            conditions.append(
                FieldCondition(key="code_metadata.symbol_name", match=MatchValue(value=symbol_name))
            )
        if access_level:
            conditions.append(FieldCondition(key="access_level", match=MatchValue(value=access_level)))

        query_filter = Filter(must=conditions) if conditions else None
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            return list(response.points)

        # Backward compatibility for older qdrant-client versions.
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
