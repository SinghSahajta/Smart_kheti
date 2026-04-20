from fastapi import APIRouter, HTTPException
from datetime import datetime

from backend.database import get_connection
from backend.models import ProfileIn, LocationIn

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

def _is_complete(profile: dict) -> bool:
    if not profile:
        return False
    required = ["location_name", "lat", "lng", "crop", "sowing_date", "has_irrigation", "farm_size_acres"]
    for k in required:
        if profile.get(k) is None or profile.get(k) == "":
            return False
    return True

@router.get("/profile")
def get_profile():
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM user_profile WHERE id=1").fetchone()
        if not row:
            return {"exists": False, "complete": False, "profile": None}
        profile = dict(row)
        return {"exists": True, "complete": _is_complete(profile), "profile": profile}
    finally:
        conn.close()

@router.post("/location")
def save_location(payload: LocationIn):
    """
    Called by map page. Saves only location immediately.
    Creates the profile row if it doesn't exist yet.
    """
    conn = get_connection()
    try:
        created_at = datetime.now().isoformat()

        # Create row if missing, else update only location fields
        conn.execute("""
            INSERT INTO user_profile (id, location_name, lat, lng, created_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                location_name=excluded.location_name,
                lat=excluded.lat,
                lng=excluded.lng
        """, (payload.location_name, payload.lat, payload.lng, created_at))

        conn.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@router.post("/profile")
def save_profile(payload: ProfileIn):
    """
    Called by onboarding page after crop + sowing date etc are filled.
    """
    conn = get_connection()
    try:
        created_at = datetime.now().isoformat()

        conn.execute("""
            INSERT INTO user_profile
              (id, location_name, lat, lng, crop, sowing_date, has_irrigation, farm_size_acres, created_at)
            VALUES
              (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              location_name=excluded.location_name,
              lat=excluded.lat,
              lng=excluded.lng,
              crop=excluded.crop,
              sowing_date=excluded.sowing_date,
              has_irrigation=excluded.has_irrigation,
              farm_size_acres=excluded.farm_size_acres,
              created_at=excluded.created_at
        """, (
            payload.location_name,
            payload.lat,
            payload.lng,
            payload.crop,
            payload.sowing_date,
            int(payload.has_irrigation),
            payload.farm_size_acres,
            created_at
        ))

        conn.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@router.post("/reset")
def reset_profile():
    conn = get_connection()
    try:
        conn.execute("DELETE FROM user_profile WHERE id=1")
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()
