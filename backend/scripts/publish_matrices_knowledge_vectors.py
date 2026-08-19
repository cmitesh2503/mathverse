from __future__ import annotations

from google import genai
from google.cloud import firestore

from services.repositories.firestore_knowledge_vector_index import (
    FirestoreKnowledgeVectorIndex,
)

# IMPORTANT:
# Import the same fixture / builders used by
# smoke_test_real_knowledge_vector_search.py.
#
# Keep these imports identical to the working smoke test.
from infrastructure.scripts.smoke_test_real_knowledge_vector_search import (
    build_real_matrices_package,
)


PROJECT_ID = "knowledge-factory-prod"
COLLECTION_NAME = "knowledge_vectors"


def main() -> None:

    print("1. Loading real Matrices KnowledgePackage...")

    package = build_real_matrices_package()

    print(
        f"   PASS: package built "
        f"document_id={package.document_id}"
    )

    print("2. Creating Vertex AI GenAI client...")

    genai_client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="global",
    )

    print("   PASS: GenAI client created")

    print("3. Creating Firestore client...")

    firestore_client = firestore.Client(
        project=PROJECT_ID
    )

    print("   PASS: Firestore client created")

    print("4. Creating vector index...")

    vector_index = FirestoreKnowledgeVectorIndex(
        client=firestore_client,
        genai_client=genai_client,
    )

    print("   PASS: vector index created")

    print("5. Publishing Matrices vectors...")

    vector_index.index(package)

    print(
        "   PASS: vectors published "
        "to Firestore"
    )

    print("6. Verifying persistent vectors...")

    collection = firestore_client.collection(
        COLLECTION_NAME
    )

    snapshots = list(
        collection.stream()
    )

    matching = [
        snapshot
        for snapshot in snapshots
        if (
            snapshot.to_dict() or {}
        ).get("document_id")
        == package.document_id
    ]

    print(
        f"   PASS: {len(matching)} "
        "vector documents found"
    )

    if not matching:
        raise RuntimeError(
            "Vector publication verification failed"
        )

    print()
    print(
        "Persistent Matrices vector publication: PASS"
    )

    print()
    print(
        "IMPORTANT: vector documents were NOT deleted."
    )


if __name__ == "__main__":
    main()