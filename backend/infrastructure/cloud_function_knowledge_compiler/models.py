from typing import List, Dict
from pydantic import BaseModel, Field

class Concept(BaseModel):

    id: str

    name: str

    chapter_id: str

    order: int

    prerequisites: List[str] = Field(default_factory=list)
    
class Chapter(BaseModel):

    id: str

    name: str

    order: int

    concepts: List[Concept] = Field(default_factory=list)


class ChapterMetadata(BaseModel):

    id: str

    name: str

    order: int

    class Config:
        extra = "forbid"


class CurriculumMetadata(BaseModel):

    exam: str

    subject: str

    grade: str

    chapters: List[ChapterMetadata] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class Curriculum(BaseModel):

    exam: str

    subject: str

    grade: str

    chapters: List[Chapter] = Field(default_factory=list)


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