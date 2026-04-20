from datetime import datetime, date

# Use unicode escape sequences for emojis to avoid Windows encoding issues
EMOJI_SEEDLING = "\U0001F331"   # 🌱
EMOJI_EAR      = "\U0001F33E"   # 🌾
EMOJI_TRACTOR  = "\U0001F69C"   # 🚜

CROP_STAGES = {
    "wheat": [
        {
            "name": "Rising Stage",
            "days_range": (0, 45),
            "emoji": EMOJI_SEEDLING,
            "description": "Germination to tillering",
            "key_threats": ["frost", "waterlogging", "aphids", "loose smut"],
            "irrigation_frequency_days": 10,
            "critical_temp_min": 5,
            "critical_temp_max": 25,
            "advice": [
                "First irrigation at crown root initiation (21 days)",
                "Apply nitrogen fertilizer in splits",
                "Watch for yellow rust in cool humid conditions",
            ],
        },
        {
            "name": "Stable Stage",
            "days_range": (45, 100),
            "emoji": EMOJI_EAR,
            "description": "Jointing to grain filling",
            "key_threats": ["powdery mildew", "stem rust", "heat stress", "lodging"],
            "irrigation_frequency_days": 15,
            "critical_temp_min": 12,
            "critical_temp_max": 30,
            "advice": [
                "Critical irrigation at heading stage - do not skip",
                "Avoid excess nitrogen - causes lodging",
                "Do NOT disturb crop during grain filling",
            ],
        },
        {
            "name": "Harvest Stage",
            "days_range": (100, 150),
            "emoji": EMOJI_TRACTOR,
            "description": "Maturity and harvest",
            "key_threats": ["unseasonal rain", "hailstorm", "price crash"],
            "irrigation_frequency_days": 0,
            "critical_temp_min": 20,
            "critical_temp_max": 40,
            "advice": [
                "Harvest when grain moisture < 14%",
                "Rain before harvest can cause sprouting",
                "Compare mandi prices before selling",
            ],
        },
    ],
    "paddy": [
        {
            "name": "Rising Stage",
            "days_range": (0, 30),
            "emoji": EMOJI_SEEDLING,
            "description": "Nursery to transplanting",
            "key_threats": ["blast disease", "stem borer", "flood", "drought"],
            "irrigation_frequency_days": 3,
            "critical_temp_min": 20,
            "critical_temp_max": 35,
            "advice": [
                "Maintain 2-3 cm standing water after transplanting",
                "Control weeds in first 30 days",
            ],
        },
        {
            "name": "Stable Stage",
            "days_range": (30, 90),
            "emoji": EMOJI_EAR,
            "description": "Vegetative to panicle initiation",
            "key_threats": ["bacterial blight", "brown planthopper", "zinc deficiency"],
            "irrigation_frequency_days": 5,
            "critical_temp_min": 22,
            "critical_temp_max": 35,
            "advice": [
                "Intermittent irrigation saves water",
                "Monitor for brown planthopper",
            ],
        },
        {
            "name": "Harvest Stage",
            "days_range": (90, 130),
            "emoji": EMOJI_TRACTOR,
            "description": "Grain filling to harvest",
            "key_threats": ["grain discoloration", "rat attack", "early rains"],
            "irrigation_frequency_days": 10,
            "critical_temp_min": 20,
            "critical_temp_max": 35,
            "advice": [
                "Stop irrigation 15 days before harvest",
                "Dry grain to about 14% moisture before storage",
            ],
        },
    ],
}

def get_current_stage(crop: str, sowing_date_str: str) -> dict:
    try:
        sowing_date = datetime.strptime(sowing_date_str, "%Y-%m-%d").date()
    except Exception:
        return {"error": "Invalid sowing date format. Use YYYY-MM-DD."}

    days_elapsed = (date.today() - sowing_date).days
    stages = CROP_STAGES.get((crop or "").lower(), [])

    for i, stage in enumerate(stages):
        start, end = stage["days_range"]
        if start <= days_elapsed < end:
            total_days = end - start
            progress = ((days_elapsed - start) / total_days) * 100
            return {
                "stage_index": i,
                "stage_name": stage["name"],
                "emoji": stage["emoji"],
                "description": stage["description"],
                "days_elapsed": days_elapsed,
                "days_in_stage": days_elapsed - start,
                "days_remaining_in_stage": end - days_elapsed,
                "progress_percent": round(min(progress, 100), 1),
                "key_threats": stage["key_threats"],
                "irrigation_frequency_days": stage["irrigation_frequency_days"],
                "critical_temp_min": stage["critical_temp_min"],
                "critical_temp_max": stage["critical_temp_max"],
                "advice": stage["advice"],
                "total_stages": len(stages),
            }

    if days_elapsed < 0:
        return {
            "stage_index": -1,
            "stage_name": "Pre-Sowing",
            "emoji": "",
            "description": "Crop not yet sown",
            "days_elapsed": days_elapsed,
            "progress_percent": 0,
            "key_threats": [],
            "advice": ["Prepare field", "Arrange inputs"],
        }

    return {
        "stage_index": len(stages),
        "stage_name": "Post Harvest",
        "emoji": "",
        "description": "Crop cycle complete",
        "days_elapsed": days_elapsed,
        "progress_percent": 100,
        "key_threats": [],
        "advice": ["Plan next season / crop rotation"],
    }


def get_stage_specific_alerts(crop: str, sowing_date: str, weather: dict) -> list:
    stage = get_current_stage(crop, sowing_date)
    if "error" in stage:
        return []

    temp = float(weather.get("current_temp", 25))
    rain_prob = float(weather.get("rain_probability_6h", 0))

    alerts = []

    if temp < stage.get("critical_temp_min", -999):
        alerts.append({
            "type": "TEMPERATURE",
            "severity": "HIGH",
            "message": f"Temperature {temp}C below critical min {stage['critical_temp_min']}C for {stage['stage_name']}.",
        })

    if temp > stage.get("critical_temp_max", 999):
        alerts.append({
            "type": "HEAT_STRESS",
            "severity": "HIGH",
            "message": f"Temperature {temp}C above critical max {stage['critical_temp_max']}C.",
        })

    if stage["stage_name"] == "Harvest Stage" and rain_prob > 50:
        alerts.append({
            "type": "HARVEST_RAIN_RISK",
            "severity": "CRITICAL",
            "message": f"Rain probability {rain_prob}% - harvest/post-harvest drying at risk.",
        })

    return alerts
