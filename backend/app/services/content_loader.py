import os
from langchain_community.document_loaders import PyPDFLoader


def load_ncert_content():
    base_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../")
)

    pdf_root = os.path.join(base_dir, "data", "pdfs")

    print("📂 Looking for PDFs in:", pdf_root)

    documents = []

    if not os.path.exists(pdf_root):
        print("❌ PDF root folder NOT FOUND")
        return []

    # 🔥 scan ALL subfolders (std 10 etc.)
    for root, dirs, files in os.walk(pdf_root):
        for file in files:
            if file.endswith(".pdf"):
                path = os.path.join(root, file)
                try:
                    loader = PyPDFLoader(path)
                    docs = loader.load()
                    documents.extend(docs)
                    print(f"✅ Loaded {file}")
                except Exception as e:
                    print(f"❌ Failed {file}: {e}")

    if not documents:
        print("❌ No PDF documents loaded")

    print(f"📊 Total documents loaded: {len(documents)}")

    return documents