def recommend(crop: str, label: str, stage: dict, weather: dict) -> dict:
    crop = (crop or "").lower()
    label = (label or "").lower()

    # weather aliases
    rain6h = weather.get("rain_probability_6h") or weather.get("next_6h", {}).get("rain_probability_max_percent", 0)
    wind = weather.get("wind") or weather.get("current", {}).get("wind_kmh", 0)

    spray_warning = None
    if rain6h and rain6h >= 40:
        spray_warning = "High rain chance soon. Avoid spraying now; spray after a dry window."
    elif wind and wind >= 15:
        spray_warning = "High wind right now. Avoid spraying to prevent drift; spray in calm hours."

    stage_name = (stage or {}).get("stage_name", "")
    stage_tip = f"Current stage: {stage_name}. Follow stage-specific precautions." if stage_name else None

    # Wheat mapping (same as before; keep)
    wheat = {
        "healthyleaf": [
            "Leaf looks healthy. Continue monitoring weekly.",
            "Avoid excess nitrogen; maintain balanced nutrients.",
        ],
        "leafblight": [
            "Remove heavily infected leaves if feasible; keep field hygiene.",
            "Avoid overhead irrigation; keep foliage dry.",
            "If spreading quickly, consult local agri officer for suitable fungicide (follow label).",
        ],
        "blackpoint": [
            "Often linked to humidity near grain filling. Avoid late irrigation if not needed.",
            "Harvest timely and dry grain properly to reduce discoloration risk.",
        ],
        "fusariumfootrot": [
            "Improve drainage; avoid waterlogging.",
            "Use crop rotation and remove infected residues.",
            "Consult local expert for seed treatment / control options if severe.",
        ],
        "wheatblast": [
            "High-risk disease. Act fast: remove infected parts if localized.",
            "Avoid dense canopy; balanced fertilizer (avoid excess nitrogen).",
            "Urgently consult local extension worker for region-approved control strategy.",
        ],
    }

    # Paddy/Rice mapping UPDATED for your new model classes
    paddy = {
        "healthy": [
            "Leaf looks healthy. No major disease detected.",
            "Maintain recommended water level; avoid both drought stress and prolonged stagnation.",
            "Use balanced fertilizer (do not overuse nitrogen). Keep monitoring weekly.",
        ],
        "brownspot": [
            "Brown spot often increases with nutrient stress. Ensure balanced fertilization (especially potassium).",
            "Avoid drought stress; maintain proper irrigation schedule.",
            "If lesions increase rapidly, consult local agri officer for fungicide guidance (follow label).",
        ],
        "leafblast": [
            "Rice leaf blast risk: avoid excess nitrogen and very dense planting.",
            "Maintain proper spacing and field sanitation; remove severely infected leaves if feasible.",
            "If spreading, consult local agri officer for region-approved fungicide timing (follow label).",
        ],
        "hispa": [
            "Rice hispa is a pest (insect). Check for scraping/white streaks and adults on leaves.",
            "Cultural control: remove weeds, avoid excessive nitrogen, use light traps if possible.",
            "If infestation is high, consult local agri officer for insecticide recommendation and safe dose (follow label).",
        ],
    }

    if crop == "wheat":
        steps = wheat.get(label, ["Unknown wheat condition. Retake clear close-up photo and consult local expert."])
    else:
        steps = paddy.get(label, ["Unknown rice condition. Retake clear close-up photo and consult local expert."])

    return {
        "steps": steps,
        "spray_warning": spray_warning,
        "stage_tip": stage_tip,
    }
