from google.cloud import firestore
from datetime import datetime, timezone

PROMO_CODE = "BETA100"
PROMO_DOC = {
    "is_active": True,
    "type": "free_trial",  # backend treats this as 100% free
    "value": 100,
    "expiry_date": "2026-07-04T00:00:00Z",
    "max_uses": 100,
    "current_uses": 0,
    "description": "30-day free trial promo for testing (BETA100)"
}


def main():
    db = firestore.Client()
    doc_ref = db.collection("promocodes").document(PROMO_CODE)
    doc_ref.set(PROMO_DOC)
    print(f"Created/updated promo: {PROMO_CODE}")


if __name__ == '__main__':
    main()
