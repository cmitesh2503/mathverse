import json
import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Dynamically build the absolute path to your key
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(BASE_DIR, "app", "core", "firebase_key.json")

print(f"Looking for Firebase key at: {key_path}")

# Initialize Firebase
if not os.path.exists(key_path):
    print("❌ ERROR: The firebase_key.json file does not exist at the path above!")
    exit(1)

cred = credentials.Certificate(key_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. Dynamically build the path to the curriculum folder
CURRICULUM_DIR = Path(os.path.join(BASE_DIR, "app", "data", "curriculum"))

def migrate_curriculum():
    print("Starting migration to Firestore from JSON files...")
    
    if not CURRICULUM_DIR.exists():
        print(f"❌ Error: Directory {CURRICULUM_DIR} does not exist.")
        return

    for json_file in CURRICULUM_DIR.glob("*.json"):
        doc_name = json_file.stem
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if isinstance(data, list):
                db.collection("curriculums").document(doc_name).set({"chapters": data})
            else:
                db.collection("curriculums").document(doc_name).set(data)
                
            print(f"✅ Successfully uploaded {doc_name} to Firestore!")
            
        except Exception as e:
            print(f"❌ Failed to upload {doc_name}: {e}")

    print("Migration complete! You can now check your Firebase Console.")

if __name__ == "__main__":
    migrate_curriculum()