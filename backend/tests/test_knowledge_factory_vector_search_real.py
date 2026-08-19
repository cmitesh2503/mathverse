from __future__ import annotations

from google import genai

from app.core import config
from app.services.knowledge_factory.knowledge_factory_client import (
    KnowledgeFactoryClient,
)


QUERY = "What is a matrix?"

EXPECTED_DOCUMENT_ID = (
    "doc-a349417c44b68bf3886412b04e25788c"
)

EMBEDDING_MODEL = "gemini-embedding-001"


def main() -> None:

    print(
        "1. Creating MathVerse Vertex AI client..."
    )

    genai_client = genai.Client(
        vertexai=True,
        project=(
            config.KNOWLEDGE_FACTORY_PROJECT_ID
        ),
        location="global",
    )

    print(
        "   PASS: GenAI client created"
    )

    print(
        "2. Generating query embedding..."
    )

    response = (
        genai_client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=QUERY,
            config={
                "output_dimensionality": 768,
            },
        )
    )

    query_vector = (
        response.embeddings[0].values
    )

    print(
        f"   PASS: embedding generated "
        f"({len(query_vector)} dimensions)"
    )

    assert len(query_vector) == 768

    print(
        "3. Creating KnowledgeFactoryClient..."
    )

    client = KnowledgeFactoryClient(
        project_id=(
            config.KNOWLEDGE_FACTORY_PROJECT_ID
        ),
        collection_name=(
            config.KNOWLEDGE_FACTORY_VECTOR_COLLECTION
        ),
    )

    print(
        "   PASS: client created"
    )

    print(
        "4. Running real Knowledge Factory "
        "vector search..."
    )

    print(
        f"   query: {QUERY!r}"
    )

    results = client.search(
        query_vector,
        top_k=3,
    )

    print(
        f"   PASS: {len(results)} results returned"
    )

    assert results

    print()
    print(
        "5. Inspecting results..."
    )

    for index, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"--- Result {index} ---"
        )

        print(
            f"document_id : "
            f"{result.document_id}"
        )

        print(
            f"source_id   : "
            f"{result.source_id}"
        )

        print(
            f"type        : "
            f"{result.knowledge_type}"
        )

        print(
            f"distance    : "
            f"{result.distance}"
        )

        print(
            f"text        : "
            f"{result.text}"
        )

        print()

    print(
        "6. Verifying Matrices knowledge..."
    )

    top_result = results[0]

    assert (
        top_result.document_id
        == EXPECTED_DOCUMENT_ID
    )

    assert (
        top_result.knowledge_type
        == "concept"
    )

    assert top_result.text

    print(
        "   PASS: top result is published "
        "Matrices knowledge"
    )

    print()
    print(
        "MathVerse → Knowledge Factory "
        "Vector Search test: PASS"
    )


if __name__ == "__main__":
    main()