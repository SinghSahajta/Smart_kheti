from fastapi import APIRouter, HTTPException

from backend.database import get_connection
from backend.services.weather_service import get_weather_bundle
from backend.services.crop_stage import get_current_stage, get_stage_specific_alerts
from backend.services.moisture_model import estimate_moisture

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

def _get_profile_or_400():
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM user_profile WHERE id=1").fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="No user profile found. Complete onboarding first.")
        return dict(row)
    finally:
        conn.close()

@router.get("/weather")
def dashboard_weather():
    profile = _get_profile_or_400()
    return get_weather_bundle(profile["lat"], profile["lng"])

@router.get("/stage")
def dashboard_stage():
    profile = _get_profile_or_400()
    return get_current_stage(profile["crop"], profile["sowing_date"])

@router.get("/moisture")
def dashboard_moisture():
    profile = _get_profile_or_400()
    weather = get_weather_bundle(profile["lat"], profile["lng"])

    has_irrigation_bool = int(profile["has_irrigation"]) in (1, 2)

    return estimate_moisture(
        last_rain_mm=weather["rain"]["last_rain_mm"],
        days_since_rain=weather["rain"]["days_since_rain"],
        temperature=weather["current"]["temp_c"],
        humidity=weather["current"]["humidity_percent"],
        has_irrigation=has_irrigation_bool,
        days_since_irrigation=999
    )

@router.get("/status")
def dashboard_status():
    profile = _get_profile_or_400()
    weather = get_weather_bundle(profile["lat"], profile["lng"])
    stage = get_current_stage(profile["crop"], profile["sowing_date"])

    has_irrigation_bool = int(profile["has_irrigation"]) in (1, 2)
    moisture = estimate_moisture(
        last_rain_mm=weather["rain"]["last_rain_mm"],
        days_since_rain=weather["rain"]["days_since_rain"],
        temperature=weather["current"]["temp_c"],
        humidity=weather["current"]["humidity_percent"],
        has_irrigation=has_irrigation_bool,
    )

    stage_alerts = get_stage_specific_alerts(
        crop=profile["crop"],
        sowing_date=profile["sowing_date"],
        weather={
            "current_temp": weather["current"]["temp_c"],
            "humidity": weather["current"]["humidity_percent"],
            "rain_probability_6h": weather["next_6h"]["rain_probability_max_percent"],
        }
    )

    moisture_alert = None
    if moisture.get("needs_irrigation"):
        moisture_alert = {
            "type": "IRRIGATION",
            "severity": "HIGH" if moisture.get("status") == "LOW" else "CRITICAL",
            "message": f"Moisture index is {moisture['estimated_moisture_percent']}% ({moisture['status']}). Irrigation likely needed.",
            "action": "Irrigate in early morning/evening; avoid midday heat."
        }

    alerts = stage_alerts[:]
    if moisture_alert:
        alerts.insert(0, moisture_alert)

    return {
        "profile": profile,
        "weather": weather,
        "stage": stage,
        "moisture": moisture,
        "alerts_preview": alerts
    }
