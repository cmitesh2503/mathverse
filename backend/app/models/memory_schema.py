from typing import List

from pydantic import BaseModel


class MemorySchema(BaseModel):

    current_topic: str

    explained_topics: List[str]

    misconceptions: List[str]

    teaching_methods_used: List[str]

    learning_status: str