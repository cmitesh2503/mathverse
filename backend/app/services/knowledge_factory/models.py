from pydantic import BaseModel, Field
from typing import List, Dict


class ExtractionResult(BaseModel):

    success: bool = True

    document_type: str

    metadata: Dict = Field(default_factory=dict)

    data: Dict = Field(default_factory=dict)

    warnings: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):

    valid: bool

    errors: List[str] = Field(default_factory=list)


class KnowledgeGraphResult(BaseModel):

    nodes_created: int = 0

    relationships_created: int = 0