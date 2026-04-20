from datetime import datetime

def estimate_moisture(
    last_rain_mm: float,
    days_since_rain: int,
    temperature: float,
    humidity: float,
    has_irrigation: bool,
    days_since_irrigation: int = 999
) -> dict:
    last_rain_mm = float(last_rain_mm or 0.0)
    days_since_rain = int(days_since_rain or 0)

    rain_contribution = min(last_rain_mm * 1.5, 45.0)

    if temperature > 35:
        daily_et = 4.0
    elif temperature > 30:
        daily_et = 3.0
    elif temperature > 25:
        daily_et = 2.5
    elif temperature > 20:
        daily_et = 2.0
    else:
        daily_et = 1.5

    humidity_factor = 1.0 - (float(humidity) / 200.0)
    daily_et *= humidity_factor

    moisture_loss = daily_et * days_since_rain

    irrigation_contribution = 0.0
    if has_irrigation and days_since_irrigation < 10:
        irrigation_contribution = max(0.0, 25.0 - (daily_et * days_since_irrigation))

    base = 40.0
    moisture = base + rain_contribution + irrigation_contribution - moisture_loss
    moisture = max(5.0, min(80.0, moisture))

    if moisture < 15:
        status = "CRITICAL"
        color = "#dc2626"
        needs_irrigation = True
    elif moisture < 25:
        status = "LOW"
        color = "#f59e0b"
        needs_irrigation = True
    elif moisture < 50:
        status = "NORMAL"
        color = "#16a34a"
        needs_irrigation = False
    else:
        status = "HIGH"
        color = "#2563eb"
        needs_irrigation = False

    return {
        "estimated_moisture_percent": round(moisture, 1),
        "status": status,
        "status_color": color,
        "needs_irrigation": needs_irrigation,
        "model": "AI Estimated Moisture Index (Evapotranspiration Model)",
        "timestamp": datetime.now().isoformat(),
    }
