from fastapi import APIRouter, HTTPException
from datetime import datetime

from backend.database import get_connection
from backend.services.weather_service import get_weather_bundle
from backend.services.crop_stage import get_current_stage, get_stage_specific_alerts
from backend.services.moisture_model import estimate_moisture

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

def _get_profile_or_400():
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM user_profile WHERE id=1").fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="No user profile found. Complete onboarding first.")
        return dict(row)
    finally:
        conn.close()

def _persist_alerts(stage_name: str, alerts: list) -> int:
    if not alerts:
        return 0
    conn = get_connection()
    inserted = 0
    try:
        for a in alerts:
            atype = a.get("type", "GENERAL")
            severity = a.get("severity", "INFO")
            message = a.get("message", "")
            stg = stage_name or ""

            # de-dup exact active alert
            exists = conn.execute("""
                SELECT id FROM alerts
                WHERE user_id=1 AND dismissed=0
                  AND type=? AND severity=? AND message=? AND stage=?
                LIMIT 1
            """, (atype, severity, message, stg)).fetchone()
            if exists:
                continue

            conn.execute("""
                INSERT INTO alerts (user_id, type, severity, message, stage, timestamp, dismissed)
                VALUES (1, ?, ?, ?, ?, ?, 0)
            """, (atype, severity, message, stg, datetime.now().isoformat()))
            inserted += 1

        conn.commit()
        return inserted
    finally:
        conn.close()

@router.post("/generate")
def generate_alerts():
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
        }

    alerts = stage_alerts[:]
    if moisture_alert:
        alerts.insert(0, moisture_alert)

    # If nothing detected, store a friendly "system ok" message
    if not alerts:
        alerts = [{
            "type": "SYSTEM",
            "severity": "INFO",
            "message": "No major risks detected for current crop stage. Keep monitoring weather and moisture."
        }]

    stage_name = stage.get("stage_name", "") if isinstance(stage, dict) else ""
    inserted = _persist_alerts(stage_name, alerts)

    return {
        "ok": True,
        "inserted": inserted,
        "generated": alerts,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/active")
def get_active(limit: int = 50):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM alerts
            WHERE user_id=1 AND dismissed=0
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return {"items": [dict(r) for r in rows]}
    finally:
        conn.close()

@router.get("/history")
def get_history(limit: int = 200):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM alerts
            WHERE user_id=1
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return {"items": [dict(r) for r in rows]}
    finally:
        conn.close()

@router.post("/dismiss/{alert_id}")
def dismiss(alert_id: int):
    conn = get_connection()
    try:
        cur = conn.execute("UPDATE alerts SET dismissed=1 WHERE id=? AND user_id=1", (alert_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"ok": True}
    finally:
        conn.close()

@router.post("/dismiss_all")
def dismiss_all():
    conn = get_connection()
    try:
        conn.execute("UPDATE alerts SET dismissed=1 WHERE user_id=1 AND dismissed=0")
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()

