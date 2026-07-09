from pathlib import Path

from app.services.knowledge_factory.azure_layout_service import (
    AzureLayoutService,
)

pdf = Path(
    "temp/matrices/chunk_001.pdf"
)

service = AzureLayoutService()

markdown = service.analyze(pdf)

print()

print("=" * 80)
print(markdown)

print("=" * 80)

print(markdown.read_text()[:2000])