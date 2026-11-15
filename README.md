# Smart Agriculture Monitoring

A desktop AI agriculture prototype that combines leaf disease detection, crop yield prediction, fertilizer recommendation, weather impact forecasting, and drone/satellite-style farm imagery monitoring.

## Features

- Upload a crop leaf image and detect likely disease symptoms from visible color patterns.
- Predict expected yield from crop, acreage, soil NPK, pH, rainfall, temperature, humidity, and previous yield.
- Recommend NPK fertilizer correction and pH-aware agronomy guidance.
- Forecast weather impact risk and field actions.
- Upload drone or satellite imagery to estimate canopy coverage, vegetation index, and stressed zones.
- Includes generated sample leaf and farm images so the dashboard works on first launch.

## Run

```powershell
pip install -r requirements_smart_agriculture.txt
python run_smart_agriculture_monitoring.py
```

This is a decision-support prototype. Field recommendations should be validated with local agronomists, crop stage, soil reports, and approved product labels before farm application.
