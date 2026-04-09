# =========================
# ✅ IMPORTS
# =========================

from typing import Optional

from .lesson_state import LessonState
from ..services.content_loader import load_ncert_content

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


# =========================
# ✅ INIT RAG (GLOBAL)
# =========================

retriever = None

def init_cbse():
    global retriever

    if retriever is not None:
        return

    print("📚 Initializing CBSE knowledge base...")

    try:
        documents = load_ncert_content()

        if not documents:
            print("❌ No documents found")
            return

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100
        )

        chunks = splitter.split_documents(documents)

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        vectorstore = FAISS.from_documents(chunks, embeddings)

        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        print(f"✅ CBSE loaded: {len(chunks)} chunks")

    except Exception as e:
        print(f"❌ CBSE init failed: {e}")
    
# =========================
# ✅ TUTOR ENGINE CLASS
# =========================

class TutorEngine:

    def __init__(self):
        pass

    # -------------------------
    # 🔍 RAG HELPER
    # -------------------------
    def _get_cbse_context(self, query: str) :
        if not retriever:
            return ""

        try:
            docs = retriever.get_relevant_documents(query)
            print("📚 Retrieved docs:", len(docs))

            return "\n\n".join([doc.page_content for doc in docs])

        except Exception as e:
            print("❌ Retrieval error:", e)
            return ""
    """
    def hydrate_session(self, session_id, session):
        # Minimal safe implementation
        print(f"🧠 Hydrating session: {session_id}")

        # attach basic state if needed
        return {
            "session_id": session_id,
            "status": "initialized"
        }
    """
    
    def hydrate_session(self, session_id, session):
        print("Hydration skipped for fast startup")
        return

    # -------------------------
    # 🧠 MAIN RESPONSE LOGIC
    # -------------------------
    def generate_response(self, message: str, state: Optional[LessonState] = None) -> str:

        context = self._get_cbse_context(message)

        # 🔥 Basic teaching prompt
        prompt = f"""
You are Ava, a CBSE Mathematics teacher.

Use the NCERT content below when relevant.

NCERT Content:
{context}

Student question:
{message}

Explain step-by-step in a simple way.
Keep answer short and clear.
"""

        # ⚠️ Replace this with your actual LLM call if needed
        return self._mock_llm(prompt)

    # -------------------------
    # 🤖 MOCK LLM (SAFE FALLBACK)
    # -------------------------
    def _mock_llm(self, prompt: str) -> str:
        # Replace later with actual LLM (OpenAI / Gemini etc.)
        return "📘 Based on NCERT: " + prompt[:200]
    
    def snapshot(self, session_id):
    # Minimal safe snapshot for now
        return {
            "session_id": session_id,
            "lesson_stage": "INTRO",
            "messages": [],
            "whiteboard": []
        }