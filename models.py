"""Core data models for farm monitoring decisions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldInputs:
    crop: str
    area_acres: float
    soil_n: float
    soil_p: float
    soil_k: float
    ph: float
    rainfall_mm: float
    temperature_c: float
    humidity_pct: float
    previous_yield_tons: float


@dataclass(frozen=True)
class DiseaseResult:
    label: str
    confidence: float
    severity: str
    details: str
    treatment: str


@dataclass(frozen=True)
class YieldResult:
    expected_tons: float
    tons_per_acre: float
    confidence: float
    drivers: list[str]


@dataclass(frozen=True)
class FertilizerPlan:
    title: str
    npk_kg_per_acre: tuple[int, int, int]
    guidance: list[str]


@dataclass(frozen=True)
class WeatherImpact:
    risk_level: str
    score: int
    alerts: list[str]
    actions: list[str]


@dataclass(frozen=True)
class ImageryResult:
    vegetation_index: float
    stress_level: str
    coverage_pct: float
    water_stress_pct: float
    disease_stress_pct: float
    recommendation: str

