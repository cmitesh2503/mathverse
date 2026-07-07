from app.services.knowledge_factory.models import (
    KnowledgeGraphResult
)


class GraphBuilder:

    def build(
        self,
        extraction
    ):

        return KnowledgeGraphResult(
            nodes_created=0,
            relationships_created=0
        )