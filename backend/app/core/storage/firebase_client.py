import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("backend/app/core/storage/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
