from google.cloud import firestore
from datetime import datetime, timezone


def main():
    db = firestore.Client()
    now = datetime.now(timezone.utc)

    found = False
    for doc in db.collection("promocodes").stream():
        d = doc.to_dict()
        is_active = d.get("is_active", False)
        expiry = d.get("expiry_date")
        value = d.get("value", 0)
        ptype = d.get("type")
        expired = False
        if expiry:
            try:
                expiry_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                expired = now > expiry_dt
            except Exception:
                # ignore parse errors
                expired = False
        if is_active and not expired and (ptype == "free_trial" or (isinstance(value, (int, float)) and value >= 100)):
            print(f"FOUND: {doc.id} -> {d}")
            found = True

    if not found:
        print("No active 100% promo codes found.")


if __name__ == '__main__':
    main()
