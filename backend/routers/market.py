from fastapi import APIRouter, HTTPException
from backend.database import get_connection
from backend.services.market_service import generate_market_analysis

router = APIRouter(prefix="/api/market", tags=["market"])

def _get_profile_or_400():
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM user_profile WHERE id=1").fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="No user profile found. Complete onboarding first.")
        return dict(row)
    finally:
        conn.close()

@router.get("/analysis")
def market_analysis():
    profile = _get_profile_or_400()
    return generate_market_analysis(profile["crop"])
