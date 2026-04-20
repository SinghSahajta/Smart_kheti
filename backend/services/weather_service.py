import json
from datetime import datetime, timezone
import requests

from backend.database import get_connection

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 15 * 60  # 15 minutes


def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def _is_cache_valid(cached_at_iso: str) -> bool:
    try:
        cached_at = datetime.fromisoformat(cached_at_iso.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - cached_at.astimezone(timezone.utc)
        return age.total_seconds() < CACHE_TTL_SECONDS
    except Exception:
        return False


def _get_cache():
    conn = get_connection()
    try:
        row = conn.execute("SELECT data, cached_at FROM weather_cache WHERE id=1").fetchone()
        if not row:
            return None
        if not _is_cache_valid(row["cached_at"]):
            return None
        return json.loads(row["data"])
    finally:
        conn.close()


def _set_cache(data: dict):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO weather_cache (id, data, cached_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET data=excluded.data, cached_at=excluded.cached_at
            """,
            (json.dumps(data), _utcnow_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def _build_forecast_6d(open_meteo_daily: dict) -> list:
    times = open_meteo_daily.get("time", []) or []
    tmax = open_meteo_daily.get("temperature_2m_max", []) or []
    tmin = open_meteo_daily.get("temperature_2m_min", []) or []
    psum = open_meteo_daily.get("precipitation_sum", []) or []
    pprob = open_meteo_daily.get("precipitation_probability_max", []) or []

    start = max(0, len(times) - 6)
    out = []
    for i in range(start, len(times)):
        out.append({
            "date": times[i] if i < len(times) else None,
            "temp_max_c": float(tmax[i]) if i < len(tmax) and tmax[i] is not None else None,
            "temp_min_c": float(tmin[i]) if i < len(tmin) and tmin[i] is not None else None,
            "precip_sum_mm": float(psum[i]) if i < len(psum) and psum[i] is not None else None,
            "precip_prob_max_percent": int(pprob[i]) if i < len(pprob) and pprob[i] is not None else None,
        })
    return out


def _add_ui_aliases(bundle: dict):
    """
    Adds a LOT of alias keys so any frontend can read weather without exact schema coupling.
    This is specifically to support Antigravity-generated dashboards.
    """
    cur = bundle.get("current", {}) or {}
    next6 = bundle.get("next_6h", {}) or {}

    temp_c = float(cur.get("temp_c", 0.0))
    hum = float(cur.get("humidity_percent", 0.0))
    wind = float(cur.get("wind_kmh", 0.0))
    rain6h = int(next6.get("rain_probability_max_percent", 0))

    # Existing aliases (top-level)
    bundle["current_temp"] = temp_c
    bundle["humidity"] = hum
    bundle["wind"] = wind
    bundle["rain_probability_6h"] = rain6h
    bundle["feels_like_c"] = temp_c

    # Common UI aliases (top-level)
    bundle["temp"] = temp_c
    bundle["temperature"] = temp_c
    bundle["humidity_percent"] = hum
    bundle["wind_kmh"] = wind
    bundle["rain6h"] = rain6h
    bundle["feels"] = temp_c

    # Common UI aliases (nested under current)
    cur["temp"] = temp_c
    cur["temperature"] = temp_c
    cur["humidity"] = hum
    cur["wind"] = wind
    cur["feels"] = temp_c
    cur["rain6h"] = rain6h
    bundle["current"] = cur

    # Forecast aliases
    if "forecast_6d" in bundle:
        bundle["forecast"] = bundle["forecast_6d"]  # many frontends expect weather.forecast (array)


def get_weather_bundle(lat: float, lng: float) -> dict:
    cached = _get_cache()
    if cached:
        cached["cache"] = {"hit": True}
        _add_ui_aliases(cached)   # IMPORTANT: apply aliases even when cached
        return cached

    params = {
        "latitude": lat,
        "longitude": lng,
        "timezone": "auto",
        "forecast_days": 6,
        "past_days": 7,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "hourly": "precipitation_probability,precipitation,temperature_2m,relative_humidity_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
    }

    r = requests.get(OPEN_METEO_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    current = data.get("current", {}) or {}
    hourly = data.get("hourly", {}) or {}
    daily = data.get("daily", {}) or {}

    rain_probs = (hourly.get("precipitation_probability") or [])[:6]
    rain_prob_6h = max(rain_probs) if rain_probs else 0

    precip_sums = daily.get("precipitation_sum") or []
    past_precip = precip_sums[:7] if len(precip_sums) >= 7 else precip_sums

    days_since_rain = len(past_precip)
    last_rain_mm = 0.0
    for idx in range(len(past_precip) - 1, -1, -1):
        mm = float(past_precip[idx] or 0.0)
        if mm >= 1.0:
            days_since_rain = (len(past_precip) - 1) - idx
            last_rain_mm = mm
            break

    bundle = {
        "cache": {"hit": False},
        "location": {"lat": lat, "lng": lng},
        "current": {
            "temp_c": float(current.get("temperature_2m", 0.0)),
            "humidity_percent": float(current.get("relative_humidity_2m", 0.0)),
            "wind_kmh": float(current.get("wind_speed_10m", 0.0)),
            "precip_mm": float(current.get("precipitation", 0.0)),
            "time": current.get("time"),
        },
        "next_6h": {"rain_probability_max_percent": int(rain_prob_6h)},
        "forecast_daily": {
            "time": daily.get("time", []),
            "temp_max_c": daily.get("temperature_2m_max", []),
            "temp_min_c": daily.get("temperature_2m_min", []),
            "precip_sum_mm": daily.get("precipitation_sum", []),
            "precip_prob_max_percent": daily.get("precipitation_probability_max", []),
        },
        "forecast_6d": _build_forecast_6d(daily),
        "rain": {
            "days_since_rain": int(days_since_rain),
            "last_rain_mm": float(last_rain_mm),
        },
        "source": "open-meteo",
        "fetched_at": _utcnow_iso(),
    }

    _add_ui_aliases(bundle)
    _set_cache(bundle)
    return bundle
