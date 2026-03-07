from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class TextMetadata(BaseModel):
    document_type: Optional[str] = None
    section: Optional[str] = None
    author: Optional[str] = None


class FunctionParameter(BaseModel):
    name: str
    type: Optional[str] = None


class CodeMetadata(BaseModel):
    language: Optional[str] = None
    ast_type: Optional[str] = None
    symbol_name: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    base_classes: Optional[list[str]] = None
    methods: Optional[list[str]] = None
    parameters: Optional[list[FunctionParameter]] = None
    calls: Optional[list[str]] = None
    docstring: Optional[str] = None


class GlobalMetadata(BaseModel):
    last_modified: Optional[datetime] = None
    indexed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Payload(BaseModel):
    node_type: Literal["text", "code"]
    content: str
    content_hash: str
    source_id: str
    chunk_index: int
    parent_node_id: Optional[str] = None
    hierarchy_path: Optional[str] = None
    access_level: Literal["public", "internal", "admin"] = "internal"
    text_metadata: Optional[TextMetadata] = None
    code_metadata: Optional[CodeMetadata] = None
    metadata: GlobalMetadata

    @model_validator(mode="after")
    def validate_node_specific_metadata(self) -> "Payload":
        if self.node_type == "text" and self.code_metadata is not None:
            raise ValueError("code_metadata must be null for text nodes")
        if self.node_type == "code" and self.text_metadata is not None:
            raise ValueError("text_metadata must be null for code nodes")
        return self


class VectorNode(BaseModel):
    id: str
    vector: list[float]
    payload: Payload
