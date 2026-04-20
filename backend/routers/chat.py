from fastapi import APIRouter, HTTPException
from datetime import datetime
import random

from backend.database import get_connection
from backend.services.crop_stage import get_current_stage
from backend.services.weather_service import get_weather_bundle
from backend.services.moisture_model import estimate_moisture

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_profile_or_400():
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM user_profile WHERE id=1").fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="No user profile found. Complete onboarding first.")
        return dict(row)
    finally:
        conn.close()


def _store(role: str, msg: str):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO chat_history (user_id, role, message, timestamp) VALUES (1, ?, ?, ?)",
            (role, msg, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def _intent(text: str) -> str:
    t = (text or "").strip().lower()

    # Greetings / small talk
    if t in {"hi", "hello", "hey", "hii", "hlo"} or any(k in t for k in ["namaste", "ram ram", "good morning", "good evening"]):
        return "greeting"
    if any(k in t for k in ["thanks", "thank you", "shukriya", "dhanyavaad"]):
        return "thanks"

    # Weekly plan
    if any(k in t for k in ["this week", "iss hafte", "is hafte", "week plan", "what should i do this week", "aaj kya karu", "kya karna chahiye"]):
        return "weekly_plan"

    # Specific intents
    if any(k in t for k in ["irrig", "paani", "water", "sinchai", "sichai"]):
        return "irrigation"
    if any(k in t for k in ["harvest", "kat", "kati", "cut", "combine", "thresh", "maturity"]):
        return "harvest"
    if any(k in t for k in ["pest", "keet", "insect", "hispa", "aphid", "planthopper", "borer", "rust", "blast", "spot", "blight", "disease"]):
        return "pest_disease"
    if any(k in t for k in ["fert", "urea", "dap", "npk", "nitrogen", "phosph", "potash", "khaad", "khad", "nutrient"]):
        return "nutrients"
    if any(k in t for k in ["price", "mandi", "sell", "market", "msp"]):
        return "market"
    if any(k in t for k in ["weather", "rain", "barish", "temperature", "temp", "wind", "humidity"]):
        return "weather"

    return "general"


def _ctx(profile: dict, stage: dict, weather: dict, moisture: dict) -> str:
    cur = weather.get("current", {}) or {}
    next6 = weather.get("next_6h", {}) or {}

    temp = weather.get("current_temp", cur.get("temp_c", "--"))
    hum = weather.get("humidity", cur.get("humidity_percent", "--"))
    rain6 = weather.get("rain_probability_6h", next6.get("rain_probability_max_percent", "--"))

    return (
        f"Crop: {profile.get('crop')} | Stage: {stage.get('stage_name','--')}\n"
        f"Temp: {temp}C | Humidity: {hum}% | Rain(6h): {rain6}%\n"
        f"Moisture: {moisture.get('estimated_moisture_percent','--')}% ({moisture.get('status','--')})"
    )


def _reply_greeting(profile, stage) -> str:
    greetings = [
        "Namaste! Main aapka Farm Agent hoon.",
        "Hello! Main aapki farming help ke liye yahan hoon.",
        "Namaste! Chaliye aaj ka plan dekhte hain."
    ]
    lines = [
        random.choice(greetings),
        f"Your crop is {profile.get('crop')} and stage is {stage.get('stage_name','--')}.",
        "",
        "Try asking:",
        "- Irrigation today?",
        "- Any pest risk now?",
        "- What should I do this week?",
        "- When should I harvest?"
    ]
    return "\n".join(lines)


def _reply_thanks() -> str:
    return "You are welcome. Agar aap chaho toh main irrigation / pest / harvest ka quick plan bhi de sakta hoon."


def _reply_weekly(stage, weather, moisture) -> str:
    adv = stage.get("advice") or []
    rain6 = weather.get("rain_probability_6h", weather.get("next_6h", {}).get("rain_probability_max_percent", 0))
    needs = bool(moisture.get("needs_irrigation", False))

    lines = ["This week plan (stage-aware):"]
    if adv:
        for a in adv[:3]:
            lines.append(f"- {a}")
    else:
        lines.append("- Monitor crop twice this week (leaves + pests).")
        lines.append("- Keep irrigation and nutrients balanced.")

    if needs:
        if rain6 and rain6 >= 40:
            lines.append(f"- Moisture is low but rain chance is {rain6}%. Wait for rain; irrigate only if rain misses.")
        else:
            lines.append("- Moisture is low. Plan irrigation in early morning/evening.")
    else:
        lines.append("- Moisture looks OK. No urgent irrigation needed.")

    return "\n".join(lines)


def _reply_irrigation(stage, weather, moisture) -> str:
    rain6 = weather.get("rain_probability_6h", weather.get("next_6h", {}).get("rain_probability_max_percent", 0))
    needs = bool(moisture.get("needs_irrigation", False))
    lines = ["Irrigation guidance:"]
    if stage.get("stage_name") == "Harvest Stage":
        lines.append("- You are in Harvest Stage. Usually avoid irrigation unless necessary.")
    if needs:
        if rain6 and rain6 >= 40:
            lines.append(f"- Low moisture, but rain chance is {rain6}%. Delay irrigation until rain window passes.")
        else:
            lines.append("- Low moisture. Irrigation recommended (morning/evening).")
    else:
        lines.append("- Moisture OK. No urgent irrigation today.")
    return "\n".join(lines)


def _reply_harvest(profile, stage) -> str:
    crop = (profile.get("crop") or "").lower()
    lines = ["Harvest guidance:"]
    lines.append(f"- Current stage: {stage.get('stage_name','--')}")
    if stage.get("stage_name") != "Harvest Stage":
        lines.append("- Not harvest stage yet. Focus on current stage actions.")
    else:
        if crop == "paddy":
            lines.append("- Stop irrigation about 15 days before harvest (general).")
            lines.append("- Harvest at good maturity; dry grain before storage.")
        else:
            lines.append("- Harvest at maturity; avoid rains near harvest.")
    return "\n".join(lines)


def _reply_pest(stage, weather) -> str:
    hum = weather.get("humidity", weather.get("current", {}).get("humidity_percent", 0))
    threats = stage.get("key_threats") or []
    lines = ["Pest/Disease guidance:"]
    if threats:
        lines.append("- Watch for:")
        for t in threats[:5]:
            lines.append(f"  - {t}")
    lines.append(f"- Humidity: {hum}%. Higher humidity can increase fungal risk.")
    lines.append("- If you see symptoms, upload a close-up leaf photo in Plant Health.")
    return "\n".join(lines)


def _reply_nutrients(stage) -> str:
    adv = stage.get("advice") or []
    lines = ["Nutrient guidance:"]
    lines.append(f"- Stage: {stage.get('stage_name','--')}")
    if adv:
        lines.append("- Stage notes:")
        for a in adv[:3]:
            lines.append(f"  - {a}")
    lines.append("- Avoid excess nitrogen; use balanced nutrients as per local recommendation.")
    return "\n".join(lines)


def _reply_weather(weather) -> str:
    cur = weather.get("current", {}) or {}
    next6 = weather.get("next_6h", {}) or {}
    temp = weather.get("current_temp", cur.get("temp_c", "--"))
    hum = weather.get("humidity", cur.get("humidity_percent", "--"))
    wind = weather.get("wind", cur.get("wind_kmh", "--"))
    rain6 = weather.get("rain_probability_6h", next6.get("rain_probability_max_percent", "--"))
    return f"Weather now: {temp}C, Humidity {hum}%, Wind {wind} km/h, Rain(6h) {rain6}%."


def _reply_market() -> str:
    return "Open the Market page for price trend and best mandi. If you tell a target price, I can suggest hold/sell plan (demo)."


def _reply_general(profile, stage, weather, moisture) -> str:
    return (
        "Here is your current farm snapshot:\n"
        + _ctx(profile, stage, weather, moisture)
        + "\n\nAsk: irrigation today / pest risk / this week plan / harvest timing."
    )


@router.get("/history")
def chat_history():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM chat_history WHERE user_id=1 ORDER BY id ASC LIMIT 200"
        ).fetchall()
        return {"messages": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.post("/message")
def chat_message(payload: dict):
    text = (payload.get("message") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="message is required")

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

    intent = _intent(text)

    if intent == "greeting":
        answer = _reply_greeting(profile, stage)
    elif intent == "thanks":
        answer = _reply_thanks()
    elif intent == "weekly_plan":
        answer = _reply_weekly(stage, weather, moisture)
    elif intent == "irrigation":
        answer = _reply_irrigation(stage, weather, moisture)
    elif intent == "harvest":
        answer = _reply_harvest(profile, stage)
    elif intent == "pest_disease":
        answer = _reply_pest(stage, weather)
    elif intent == "nutrients":
        answer = _reply_nutrients(stage)
    elif intent == "weather":
        answer = _reply_weather(weather)
    elif intent == "market":
        answer = _reply_market()
    else:
        answer = _reply_general(profile, stage, weather, moisture)

    assistant_reply = answer  # keep it short; no repeated snapshot every time

    _store("user", text)
    _store("assistant", assistant_reply)

    return {"reply": assistant_reply, "intent": intent, "mode": "rule-based-intent-v2"}
