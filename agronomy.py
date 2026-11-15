"""Agronomy logic used by the Smart Agriculture Monitoring app.

The calculations are intentionally transparent so the prototype remains useful
without a trained private model or live farm APIs. Real deployments can replace
these functions with trained models while keeping the GUI contract stable.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from .models import DiseaseResult, FertilizerPlan, FieldInputs, ImageryResult, WeatherImpact, YieldResult


CROP_BASE_YIELD = {
    "Wheat": 1.35,
    "Rice": 1.75,
    "Maize": 1.95,
    "Cotton": 0.85,
    "Sugarcane": 28.0,
    "Soybean": 1.1,
    "Tomato": 9.0,
}

IDEAL_WEATHER = {
    "Wheat": (18, 24, 60, 450),
    "Rice": (24, 32, 75, 1100),
    "Maize": (20, 30, 65, 650),
    "Cotton": (21, 32, 55, 700),
    "Sugarcane": (24, 34, 70, 1500),
    "Soybean": (20, 30, 65, 700),
    "Tomato": (18, 29, 65, 550),
}

NPK_TARGETS = {
    "Wheat": (90, 40, 40),
    "Rice": (100, 50, 50),
    "Maize": (120, 55, 45),
    "Cotton": (80, 40, 40),
    "Sugarcane": (150, 60, 80),
    "Soybean": (25, 60, 40),
    "Tomato": (110, 70, 80),
}


def _image_array(path: Path, max_size: int = 900) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    image = ImageOps.exif_transpose(image)
    image.thumbnail((max_size, max_size))
    return np.asarray(image, dtype=np.float32) / 255.0


def analyze_leaf_image(path: str | Path) -> DiseaseResult:
    """Estimate leaf disease from image color symptoms."""

    pixels = _image_array(Path(path))
    red, green, blue = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    green_leaf = green > (red * 1.08)
    brown_leaf = (red > 0.24) & (green < 0.44) & (blue < 0.34)
    yellow_leaf = (red > 0.38) & (green > 0.34) & (blue < 0.36)
    vegetation = green_leaf | brown_leaf | yellow_leaf
    leaf_pixels = pixels[vegetation]
    if leaf_pixels.size == 0:
        return DiseaseResult(
            "No clear leaf detected",
            0.38,
            "Unknown",
            "The image does not contain enough green leaf area for reliable analysis.",
            "Retake the photo on a plain background with one leaf filling most of the frame.",
        )

    r, g, b = leaf_pixels[:, 0], leaf_pixels[:, 1], leaf_pixels[:, 2]
    yellow = (r > 0.42) & (g > 0.42) & (b < 0.34)
    brown_spots = (r > 0.25) & (g < 0.38) & (b < 0.26)
    pale = (g > 0.38) & (np.abs(r - g) < 0.16) & (b < 0.42)
    dark_mold = (r < 0.22) & (g < 0.30) & (b < 0.24)

    symptom_scores = {
        "Fungal leaf spot": float(brown_spots.mean()),
        "Nutrient chlorosis": float(yellow.mean() + pale.mean() * 0.6),
        "Blight or mildew": float(dark_mold.mean() + brown_spots.mean() * 0.45),
        "Healthy leaf": max(0.0, 0.28 - float(brown_spots.mean() + yellow.mean() + dark_mold.mean())),
    }
    label, score = max(symptom_scores.items(), key=lambda item: item[1])
    symptom_load = float(brown_spots.mean() + yellow.mean() + dark_mold.mean())
    severity_value = min(1.0, max(symptom_load * 3.2, 0.05))
    severity = "Low" if label == "Healthy leaf" else "High" if severity_value > 0.55 else "Medium" if severity_value > 0.25 else "Low"
    confidence = min(0.94, 0.58 + max(score, severity_value) * 0.48)

    treatments = {
        "Fungal leaf spot": "Remove infected leaves, improve spacing, and apply a recommended copper or bio-fungicide spray.",
        "Nutrient chlorosis": "Check nitrogen and iron availability; apply balanced nutrition and correct soil pH before heavy dosing.",
        "Blight or mildew": "Reduce canopy humidity, avoid overhead irrigation, and use a locally approved fungicide if spread continues.",
        "Healthy leaf": "Keep scouting weekly and maintain irrigation and nutrient balance.",
    }
    details = f"Detected symptom area is approximately {severity_value:.0%} of visible leaf tissue."
    return DiseaseResult(label, confidence, severity, details, treatments[label])


def predict_yield(inputs: FieldInputs) -> YieldResult:
    crop = inputs.crop if inputs.crop in CROP_BASE_YIELD else "Wheat"
    base = CROP_BASE_YIELD[crop]
    temp_low, temp_high, ideal_humidity, ideal_rainfall = IDEAL_WEATHER[crop]
    n_target, p_target, k_target = NPK_TARGETS[crop]

    temp_mid = (temp_low + temp_high) / 2
    temp_factor = max(0.58, 1 - abs(inputs.temperature_c - temp_mid) / 24)
    humidity_factor = max(0.65, 1 - abs(inputs.humidity_pct - ideal_humidity) / 120)
    rainfall_factor = max(0.55, 1 - abs(inputs.rainfall_mm - ideal_rainfall) / (ideal_rainfall * 1.7))
    nutrient_factor = min(1.18, 0.72 + (inputs.soil_n / n_target + inputs.soil_p / p_target + inputs.soil_k / k_target) / 8)
    ph_factor = max(0.68, 1 - abs(inputs.ph - 6.6) / 4.2)
    expected_history = max(inputs.area_acres * base, 0.1)
    history_factor = 1 if inputs.previous_yield_tons <= 0 else max(0.75, min(1.25, inputs.previous_yield_tons / expected_history))

    tons_per_acre = base * temp_factor * humidity_factor * rainfall_factor * nutrient_factor * ph_factor * history_factor
    expected = max(0.0, tons_per_acre * inputs.area_acres)

    drivers = [
        f"Weather suitability: {((temp_factor + humidity_factor + rainfall_factor) / 3):.0%}",
        f"Soil nutrition balance: {nutrient_factor:.0%}",
        f"Soil pH fit: {ph_factor:.0%}",
    ]
    confidence = min(0.91, 0.62 + inputs.area_acres / 250)
    return YieldResult(round(expected, 2), round(tons_per_acre, 2), confidence, drivers)


def recommend_fertilizer(inputs: FieldInputs) -> FertilizerPlan:
    crop = inputs.crop if inputs.crop in NPK_TARGETS else "Wheat"
    targets = NPK_TARGETS[crop]
    measured = (inputs.soil_n, inputs.soil_p, inputs.soil_k)
    gaps = tuple(max(0, int(round((target - value) * 0.45))) for target, value in zip(targets, measured))
    title = "Balanced NPK correction" if any(gaps) else "Maintenance dose"
    guidance = []
    labels = ("nitrogen", "phosphorus", "potassium")
    for label, gap in zip(labels, gaps):
        guidance.append(f"Apply {gap} kg/acre additional {label} equivalent." if gap else f"{label.title()} is near target; keep maintenance only.")
    if inputs.ph < 5.8:
        guidance.append("Soil is acidic; consider agricultural lime before increasing fertilizer intensity.")
    elif inputs.ph > 7.8:
        guidance.append("Soil is alkaline; prefer organic matter and micronutrient checks.")
    else:
        guidance.append("Soil pH is suitable for efficient nutrient uptake.")
    return FertilizerPlan(title, gaps, guidance)


def forecast_weather_impact(inputs: FieldInputs) -> WeatherImpact:
    crop = inputs.crop if inputs.crop in IDEAL_WEATHER else "Wheat"
    temp_low, temp_high, ideal_humidity, ideal_rainfall = IDEAL_WEATHER[crop]
    alerts: list[str] = []
    actions: list[str] = []
    score = 0

    if inputs.temperature_c > temp_high + 4:
        score += 30
        alerts.append("Heat stress can reduce flowering and grain filling.")
        actions.append("Irrigate during cooler hours and use mulching where possible.")
    elif inputs.temperature_c < temp_low - 4:
        score += 24
        alerts.append("Low temperature may slow crop growth.")
        actions.append("Avoid heavy irrigation during cold spells.")

    if inputs.rainfall_mm < ideal_rainfall * 0.45:
        score += 32
        alerts.append("Rainfall is below crop water demand.")
        actions.append("Prioritize irrigation for flowering or fruiting zones.")
    elif inputs.rainfall_mm > ideal_rainfall * 1.45:
        score += 28
        alerts.append("Excess rainfall raises waterlogging and disease risk.")
        actions.append("Check drainage and scout for fungal symptoms.")

    if inputs.humidity_pct > ideal_humidity + 18:
        score += 18
        alerts.append("High humidity increases fungal disease pressure.")
        actions.append("Improve airflow and avoid overhead irrigation.")
    elif inputs.humidity_pct < ideal_humidity - 25:
        score += 14
        alerts.append("Dry air can increase evapotranspiration.")
        actions.append("Use soil moisture checks before fertilizer application.")

    if not alerts:
        alerts.append("Weather conditions are generally favorable.")
        actions.append("Continue normal monitoring and irrigation scheduling.")

    risk = "High" if score >= 55 else "Medium" if score >= 25 else "Low"
    return WeatherImpact(risk, min(score, 100), alerts, actions)


def analyze_farm_imagery(path: str | Path) -> ImageryResult:
    """Estimate vegetation coverage and stress from drone or satellite imagery."""

    image = _image_array(Path(path), max_size=1100)
    red, green, blue = image[..., 0], image[..., 1], image[..., 2]
    exg = 2 * green - red - blue
    vegetation = exg > 0.12
    coverage = float(vegetation.mean())
    if coverage < 0.02:
        return ImageryResult(0.0, "Unknown", 0.0, 0.0, 0.0, "Upload a clearer overhead farm image with visible crop rows or canopy.")

    veg_green = green[vegetation]
    veg_red = red[vegetation]
    veg_blue = blue[vegetation]
    vari = (veg_green - veg_red) / np.maximum(veg_green + veg_red - veg_blue, 0.05)
    vegetation_index = float(np.clip(np.nanmean(vari), -1, 1))
    yellow_stress = (veg_red > 0.36) & (veg_green > 0.35) & (veg_blue < 0.28)
    water_stress = veg_green < 0.32
    disease_stress = (veg_red > veg_green * 0.9) & (veg_blue < 0.25)

    stress_score = float(yellow_stress.mean() * 0.4 + water_stress.mean() * 0.35 + disease_stress.mean() * 0.25)
    level = "High" if stress_score > 0.34 else "Medium" if stress_score > 0.16 else "Low"
    recommendation = {
        "Low": "Canopy looks stable; continue routine scouting.",
        "Medium": "Inspect yellow or dull patches and compare with soil moisture readings.",
        "High": "Prioritize ground inspection in stressed zones and consider targeted irrigation or disease control.",
    }[level]
    return ImageryResult(
        round(vegetation_index, 3),
        level,
        round(coverage * 100, 1),
        round(float(water_stress.mean()) * 100, 1),
        round(float(disease_stress.mean()) * 100, 1),
        recommendation,
    )


def create_demo_leaf(path: str | Path) -> None:
    """Create a simple sample diseased leaf image for first-run testing."""

    width, height = 640, 420
    y, x = np.ogrid[:height, :width]
    cx, cy = width / 2, height / 2
    ellipse = ((x - cx) / 220) ** 2 + ((y - cy) / 150) ** 2 <= 1
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (236, 241, 230)
    image[ellipse] = (65, 143, 56)
    rng = np.random.default_rng(42)
    for _ in range(45):
        sx, sy = rng.integers(210, 440), rng.integers(125, 300)
        radius = rng.integers(8, 24)
        spot = (x - sx) ** 2 + (y - sy) ** 2 <= radius**2
        image[spot & ellipse] = (126, 84, 36)
    Image.fromarray(image).save(path)


def create_demo_farm(path: str | Path) -> None:
    """Create a simple overhead farm image for imagery-analysis testing."""

    width, height = 760, 460
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (120, 93, 58)
    for row in range(24, height, 42):
        color = (47, 128, 58) if row < height * 0.62 else (116, 134, 54)
        image[row : row + 20, 30 : width - 30] = color
    pil_image = Image.fromarray(image)
    pil_image = ImageEnhance.Sharpness(pil_image).enhance(1.6)
    pil_image.save(path)


