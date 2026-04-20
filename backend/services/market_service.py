from datetime import date, datetime
import random

MSP = {
    "wheat": 2275,  # approx reference (can adjust)
    "paddy": 2300,  # approx reference (can adjust)
}

BASE_PRICE = {
    "wheat": 2200,
    "paddy": 2100,
}

def _seed_for_today(crop: str) -> int:
    # deterministic per day so chart doesn't change every refresh
    return int(date.today().strftime("%Y%m%d")) + sum(ord(c) for c in crop)

def generate_market_analysis(crop: str) -> dict:
    crop = (crop or "wheat").lower()
    base = BASE_PRICE.get(crop, 2000)
    msp = MSP.get(crop)

    rnd = random.Random(_seed_for_today(crop))

    # 7-day random walk (realistic-ish)
    history = []
    price = base
    for i in range(7):
        # daily change -2%..+3%
        change = rnd.uniform(-0.02, 0.03)
        price = max(1200, price * (1 + change))
        history.append({"day_index": i - 6, "price": int(price)})

    current_price = history[-1]["price"]

    # 3 mandi comparison (spread)
    mandis = [
        {"name": "Local Mandi", "price": int(current_price * rnd.uniform(0.98, 1.02))},
        {"name": "District Mandi", "price": int(current_price * rnd.uniform(0.99, 1.04))},
        {"name": "City Mandi", "price": int(current_price * rnd.uniform(0.97, 1.03))},
    ]
    best_mandi = max(mandis, key=lambda x: x["price"])

    trend = history[-1]["price"] - history[0]["price"]
    if trend > 80:
        reco = "HOLD (Uptrend)"
        best_time = "Likely better to sell in 2-4 days if trend continues."
    elif trend < -80:
        reco = "SELL (Downtrend)"
        best_time = "Consider selling soon to avoid further drop."
    else:
        reco = "HOLD (Stable)"
        best_time = "Sell in small batches; watch next 2 days."

    msp_note = None
    if msp:
        if current_price < msp:
            msp_note = f"Current price below MSP reference ({msp}). MSP procurement may be safer."
        else:
            msp_note = f"Current price above MSP reference ({msp}). Open market looks favorable."

    return {
        "crop": crop,
        "current_price": current_price,
        "msp_reference": msp,
        "msp_note": msp_note,
        "history_7d": history,
        "mandis": mandis,
        "best_mandi": best_mandi,
        "recommendation": reco,
        "best_time_to_sell": best_time,
        "timestamp": datetime.now().isoformat(),
        "mode": "demo-simulation",
    }
