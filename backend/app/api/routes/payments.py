from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, status

from ...core.firestore_client import FIRESTORE_TIMEOUT_SECONDS, get_firestore_client
from ...schemas.payment import OrderCreateRequest

router = APIRouter(prefix="/api/payments", tags=["Billing & Promos"])

BASE_PRICE_INR = 500  # Standard monthly subscription fee


def get_db():
    return get_firestore_client()

@router.post("/checkout")
async def process_subscription_checkout(payload: OrderCreateRequest):
    """
    Evaluates promotional codes and sets up a customized billing pipeline.
    Bypasses payment gateways instantly for validated 100% free testing codes.
    """
    db = get_db()
    user_ref = db.collection("users").document(payload.user_id)
    try:
        user_doc = user_ref.get(timeout=FIRESTORE_TIMEOUT_SECONDS)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Firestore unavailable during checkout lookup: {str(e)}"
        )

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile must be created prior to subscription execution."
        )

    final_price = BASE_PRICE_INR
    promo_applied = False
    promo_data = None

    # 1. PROCESS PROMO CODE IF SUPPLIED
    if payload.promo_code:
        normalized_code = payload.promo_code.strip().upper()
        promo_ref = db.collection("promocodes").document(normalized_code)
        promo_doc = promo_ref.get(timeout=FIRESTORE_TIMEOUT_SECONDS)

        if not promo_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid promotional code entered."
            )

        promo_data = promo_doc.to_dict()

        # Validate Status, Expiration, and Capacity Limits
        if not promo_data.get("is_active", False):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This promo code is inactive.")
            
        if promo_data.get("current_uses", 0) >= promo_data.get("max_uses", 9999):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This promo code has reached its maximum use capacity.")

        expiry_str = promo_data.get("expiry_date")
        if expiry_str:
            expiry_date = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expiry_date:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This promo code has expired.")

        # Compute Reductions
        promo_type = promo_data.get("type")  # "percentage", "flat", or "free_trial"
        discount_value = promo_data.get("value", 0)

        if promo_type == "free_trial" or discount_value >= 100:
            final_price = 0
        elif promo_type == "percentage":
            final_price = max(0, BASE_PRICE_INR - int(BASE_PRICE_INR * (discount_value / 100)))
        elif promo_type == "flat":
            final_price = max(0, BASE_PRICE_INR - discount_value)

        promo_applied = True

    # 2. PATH A: 100% FREE TESTING BYPASS (Zero Gateway Steps)
    if final_price == 0:
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(days=30)  # Unlocks for a 30-day billing cycle

        updated_subscription = {
            "subscription.is_active": True,
            "subscription.subscribed_grade": str(payload.grade),
            "subscription.current_period_start": start_time.isoformat(),
            "subscription.current_period_end": end_time.isoformat(),
            "subscription.last_payment_id": f"PROMO_{payload.promo_code if payload.promo_code else 'FREE'}"
        }

        # Update user's access rights instantly
        user_ref.update(updated_subscription, timeout=FIRESTORE_TIMEOUT_SECONDS)

        # Log promo use counter increment transactionally if tracking applies
        if promo_applied:
            from google.cloud import firestore

            db.collection("promocodes").document(payload.promo_code.strip().upper()).update({
                "current_uses": firestore.Increment(1)
            }, timeout=FIRESTORE_TIMEOUT_SECONDS)

        return {
            "payment_required": False,
            "status": "active",
            "message": f"Promo activated successfully! Grade {payload.grade} access is unlocked for free.",
            "final_amount_charged": 0
        }

    # 3. PATH B: STANDARD / DISCOUNTED RAZORPAY GATEWAY COUPLING
    # Amount is scaled to paisa denomination required by Razorpay (e.g. ₹400 = 40000 paise)
    amount_in_paise = final_price * 100 

    # --- RAZORPAY ORDER CALL PLACEHOLDER ---
    # In production, initialize your Razorpay client configuration here:
    # client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    # razorpay_order = client.order.create({"amount": amount_in_paise, "currency": "INR", "payment_capture": 1})
    mock_razorpay_order_id = f"order_mock_{int(datetime.now().timestamp())}"
    # ---------------------------------------

    return {
        "payment_required": True,
        "status": "created",
        "razorpay_order_id": mock_razorpay_order_id,
        "final_amount_charged": final_price,
        "message": f"Order successfully initialized with promotional discount applied."
    }
