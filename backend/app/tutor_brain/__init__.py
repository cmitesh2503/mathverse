class TutorBrain:
    def __init__(self):
        from .content_loader import load_ncert_content

        print("🧠 Initializing TutorBrain...")

        try:
            self.ncert_content = load_ncert_content()
            print(f"✅ Loaded NCERT content: {len(self.ncert_content)} documents")
        except Exception as e:
            print(f"❌ Failed to load NCERT content: {e}")
            self.ncert_content = []
