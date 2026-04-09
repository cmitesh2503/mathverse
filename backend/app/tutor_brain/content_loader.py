import os
from langchain_community.document_loaders import PyPDFLoader


import os
from langchain_community.document_loaders import PyPDFLoader


def load_ncert_content():
    
    base_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../")
)

    pdf_root = os.path.join(base_dir, "data", "pdfs")

    documents = []

    if not os.path.exists(pdf_root):
        print("❌ PDF root folder NOT FOUND")
        return []

    # 🔥 WALK THROUGH ALL SUBFOLDERS
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

    print(f"📊 Total documents loaded: {len(documents)}")
    return documents