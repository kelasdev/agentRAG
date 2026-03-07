from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from agentrag.models import CodeMetadata, GlobalMetadata, Payload, TextMetadata


def test_payload_text_rejects_code_metadata():
    with pytest.raises(ValidationError):
        Payload(
            node_type="text",
            content="hello",
            content_hash="abc",
            source_id="x.md",
            chunk_index=0,
            text_metadata=TextMetadata(document_type="md"),
            code_metadata=CodeMetadata(language="python"),
            metadata=GlobalMetadata(last_modified=datetime.now(timezone.utc)),
        )


def test_payload_code_accepts_code_metadata():
    payload = Payload(
        node_type="code",
        content="def x(): pass",
        content_hash="abc",
        source_id="x.py",
        chunk_index=0,
        code_metadata=CodeMetadata(language="python"),
        metadata=GlobalMetadata(last_modified=datetime.now(timezone.utc)),
    )
    assert payload.code_metadata is not None
