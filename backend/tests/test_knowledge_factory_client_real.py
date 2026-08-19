from app.core import config
from app.services.knowledge_factory.knowledge_factory_client import (
    KnowledgeFactoryClient,
)


DOCUMENT_ID = "doc-a349417c44b68bf3886412b04e25788c"


def main() -> None:
    print("1. Connecting to Knowledge Factory Firestore...")

    client = KnowledgeFactoryClient(
        project_id=config.KNOWLEDGE_FACTORY_PROJECT_ID,
        collection_name=config.KNOWLEDGE_FACTORY_COLLECTION,
    )

    print("   PASS: client created")

    print("2. Reading published Matrices KnowledgePackage...")

    package = client.get_knowledge_package(
        DOCUMENT_ID
    )

    assert package is not None

    print("   PASS: package retrieved")

    print("3. Verifying real knowledge...")

    assert package["document_id"] == DOCUMENT_ID

    print(
        f"   chapters : {len(package.get('chapters', []))}"
    )
    print(
        f"   sections : {len(package.get('sections', []))}"
    )
    print(
        f"   concepts : {len(package.get('concepts', []))}"
    )
    print(
        f"   formulas : {len(package.get('formulas', []))}"
    )
    print(
        f"   examples : {len(package.get('examples', []))}"
    )
    print(
        f"   exercises: {len(package.get('exercises', []))}"
    )
    print(
        f"   figures  : {len(package.get('figures', []))}"
    )

    assert len(package.get("chapters", [])) == 1
    assert len(package.get("sections", [])) == 2
    assert len(package.get("concepts", [])) == 49
    assert len(package.get("figures", [])) == 2

    print("   PASS: real knowledge verified")

    print()
    print(
        "MathVerse → Knowledge Factory Firestore test: PASS"
    )


if __name__ == "__main__":
    main()