from pydantic import BaseModel, Field
from typing import Optional

class OrderCreateRequest(BaseModel):
    user_id: str = Field(..., description="The student's unique Firebase UID")
    grade: str = Field(..., description="The standard being subscribed to, e.g., '10'")
    promo_code: Optional[str] = Field(None, description="Optional promotional coupon, e.g., 'BETA100'")