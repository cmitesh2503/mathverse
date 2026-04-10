# 🔥 GLOBAL CACHE
retriever_instance = None

def get_retriever():
    global retriever_instance

    if retriever_instance is None:
        print("🔥 Initializing RAG (only once)...")

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        db = FAISS.load_local("backend/data/faiss_index", embeddings)

        retriever_instance = db.as_retriever(search_kwargs={"k": 3})

    return retriever_instance