"""Tkinter interface for the Smart Agriculture Monitoring system."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .agronomy import (
    CROP_BASE_YIELD,
    analyze_farm_imagery,
    analyze_leaf_image,
    create_demo_farm,
    create_demo_leaf,
    forecast_weather_impact,
    predict_yield,
    recommend_fertilizer,
)
from .models import FieldInputs


class SmartAgricultureApp(tk.Tk):
    """Decision-support dashboard for crop monitoring."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Smart Agriculture Monitoring")
        self.geometry("1280x780")
        self.minsize(1080, 700)
        self.configure(bg="#101612")

        self.leaf_path: Path | None = None
        self.farm_path: Path | None = None
        self._leaf_photo: ImageTk.PhotoImage | None = None
        self._farm_photo: ImageTk.PhotoImage | None = None

        self.crop = tk.StringVar(value="Wheat")
        self.area = tk.DoubleVar(value=12.0)
        self.soil_n = tk.DoubleVar(value=58.0)
        self.soil_p = tk.DoubleVar(value=24.0)
        self.soil_k = tk.DoubleVar(value=32.0)
        self.ph = tk.DoubleVar(value=6.5)
        self.rainfall = tk.DoubleVar(value=420.0)
        self.temperature = tk.DoubleVar(value=28.0)
        self.humidity = tk.DoubleVar(value=68.0)
        self.previous_yield = tk.DoubleVar(value=14.0)

        self._build_styles()
        self._build_layout()
        self._ensure_demo_images()
        self._run_analysis()

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Root.TFrame", background="#101612")
        style.configure("Panel.TFrame", background="#1a241d", relief="flat")
        style.configure("Title.TLabel", background="#101612", foreground="#f4f7ef", font=("Segoe UI", 24, "bold"))
        style.configure("Subtle.TLabel", background="#101612", foreground="#9fb39d", font=("Segoe UI", 10))
        style.configure("PanelTitle.TLabel", background="#1a241d", foreground="#f4f7ef", font=("Segoe UI", 14, "bold"))
        style.configure("Body.TLabel", background="#1a241d", foreground="#dbe5d5", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background="#1a241d", foreground="#9fb39d", font=("Segoe UI", 9))
        style.configure("Metric.TLabel", background="#1a241d", foreground="#ffffff", font=("Segoe UI", 20, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8))
        style.configure("TCombobox", padding=6)
        style.configure("TEntry", padding=6)

    def _build_layout(self) -> None:
        header = ttk.Frame(self, style="Root.TFrame", padding=(22, 16, 22, 8))
        header.pack(fill="x")
        ttk.Label(header, text="Smart Agriculture Monitoring", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Crop disease + yield + fertilizer + weather + drone imagery", style="Subtle.TLabel").pack(side="right")

        main = ttk.Frame(self, style="Root.TFrame", padding=(22, 10, 22, 22))
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1, minsize=270)
        main.columnconfigure(1, weight=2, minsize=430)
        main.columnconfigure(2, weight=2, minsize=390)
        main.rowconfigure(0, weight=1)

        self._build_inputs(main)
        self._build_images(main)
        self._build_report(main)

    def _build_inputs(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        panel.columnconfigure(1, weight=1)
        ttk.Label(panel, text="Farm Inputs", style="PanelTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        rows = [
            ("Crop", self.crop, "combo"),
            ("Area acres", self.area, "entry"),
            ("Soil N", self.soil_n, "entry"),
            ("Soil P", self.soil_p, "entry"),
            ("Soil K", self.soil_k, "entry"),
            ("Soil pH", self.ph, "entry"),
            ("Rainfall mm", self.rainfall, "entry"),
            ("Temp C", self.temperature, "entry"),
            ("Humidity %", self.humidity, "entry"),
            ("Last yield tons", self.previous_yield, "entry"),
        ]
        for index, (label, variable, kind) in enumerate(rows, start=1):
            ttk.Label(panel, text=label, style="Muted.TLabel").grid(row=index, column=0, sticky="w", pady=5)
            if kind == "combo":
                widget = ttk.Combobox(panel, textvariable=variable, values=list(CROP_BASE_YIELD), state="readonly")
            else:
                widget = ttk.Entry(panel, textvariable=variable)
            widget.grid(row=index, column=1, sticky="ew", pady=5, padx=(10, 0))

        ttk.Button(panel, text="Analyze Farm", style="Accent.TButton", command=self._run_analysis).grid(
            row=len(rows) + 1, column=0, columnspan=2, sticky="ew", pady=(18, 8)
        )
        ttk.Label(panel, text="Values are interpreted as field-level estimates for decision support.", style="Body.TLabel", wraplength=250).grid(
            row=len(rows) + 2, column=0, columnspan=2, sticky="ew", pady=(4, 0)
        )

    def _build_images(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 14))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)
        panel.rowconfigure(5, weight=1)
        ttk.Label(panel, text="Image Monitoring", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")

        ttk.Button(panel, text="Upload Leaf Image", style="Accent.TButton", command=self._choose_leaf).grid(row=1, column=0, sticky="ew", pady=(12, 8))
        self.leaf_preview = tk.Label(panel, bg="#0b100d", fg="#dbe5d5", text="Leaf image preview", bd=0)
        self.leaf_preview.grid(row=2, column=0, sticky="nsew", pady=(0, 16))

        ttk.Button(panel, text="Upload Drone/Satellite Image", style="Accent.TButton", command=self._choose_farm).grid(row=4, column=0, sticky="ew", pady=(0, 8))
        self.farm_preview = tk.Label(panel, bg="#0b100d", fg="#dbe5d5", text="Farm imagery preview", bd=0)
        self.farm_preview.grid(row=5, column=0, sticky="nsew")

    def _build_report(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        panel.grid(row=0, column=2, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)
        ttk.Label(panel, text="AI Decision Report", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")

        self.status_label = ttk.Label(panel, text="Ready", style="Metric.TLabel")
        self.status_label.grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.summary_label = ttk.Label(panel, text="", style="Body.TLabel", wraplength=360)
        self.summary_label.grid(row=2, column=0, sticky="ew", pady=(2, 12))

        self.report = tk.Text(
            panel,
            wrap="word",
            bg="#0b100d",
            fg="#f4f7ef",
            insertbackground="#f4f7ef",
            relief="flat",
            padx=14,
            pady=12,
            font=("Segoe UI", 10),
        )
        self.report.grid(row=3, column=0, sticky="nsew")
        self.report.configure(state="disabled")

    def _ensure_demo_images(self) -> None:
        data_dir = Path(__file__).resolve().parent / "sample_data"
        data_dir.mkdir(exist_ok=True)
        self.leaf_path = data_dir / "sample_leaf.jpg"
        self.farm_path = data_dir / "sample_farm.jpg"
        if not self.leaf_path.exists():
            create_demo_leaf(self.leaf_path)
        if not self.farm_path.exists():
            create_demo_farm(self.farm_path)
        self._show_image(self.leaf_path, self.leaf_preview, "leaf")
        self._show_image(self.farm_path, self.farm_preview, "farm")

    def _choose_leaf(self) -> None:
        path = filedialog.askopenfilename(title="Select leaf image", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if path:
            self.leaf_path = Path(path)
            self._show_image(self.leaf_path, self.leaf_preview, "leaf")
            self._run_analysis()

    def _choose_farm(self) -> None:
        path = filedialog.askopenfilename(title="Select drone or satellite image", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if path:
            self.farm_path = Path(path)
            self._show_image(self.farm_path, self.farm_preview, "farm")
            self._run_analysis()

    def _show_image(self, path: Path, label: tk.Label, target: str) -> None:
        image = Image.open(path).convert("RGB")
        image.thumbnail((440, 230))
        photo = ImageTk.PhotoImage(image)
        if target == "leaf":
            self._leaf_photo = photo
        else:
            self._farm_photo = photo
        label.configure(image=photo, text="")

    def _inputs(self) -> FieldInputs:
        return FieldInputs(
            crop=self.crop.get(),
            area_acres=max(0.1, float(self.area.get())),
            soil_n=max(0, float(self.soil_n.get())),
            soil_p=max(0, float(self.soil_p.get())),
            soil_k=max(0, float(self.soil_k.get())),
            ph=max(3.5, min(10.0, float(self.ph.get()))),
            rainfall_mm=max(0, float(self.rainfall.get())),
            temperature_c=float(self.temperature.get()),
            humidity_pct=max(0, min(100, float(self.humidity.get()))),
            previous_yield_tons=max(0, float(self.previous_yield.get())),
        )

    def _run_analysis(self) -> None:
        try:
            inputs = self._inputs()
            leaf = analyze_leaf_image(self.leaf_path) if self.leaf_path else None
            farm = analyze_farm_imagery(self.farm_path) if self.farm_path else None
            yield_result = predict_yield(inputs)
            fertilizer = recommend_fertilizer(inputs)
            weather = forecast_weather_impact(inputs)
        except Exception as exc:
            messagebox.showerror("Analysis Error", str(exc))
            return

        self.status_label.configure(text=f"{weather.risk_level} Risk")
        self.summary_label.configure(text=f"Expected yield: {yield_result.expected_tons} tons across {inputs.area_acres:g} acres")

        lines = [
            "CROP DISEASE DETECTION",
            f"Result: {leaf.label} ({leaf.confidence:.0%} confidence)",
            f"Severity: {leaf.severity}",
            leaf.details,
            f"Treatment: {leaf.treatment}",
            "",
            "YIELD PREDICTION",
            f"Expected production: {yield_result.expected_tons} tons",
            f"Productivity: {yield_result.tons_per_acre} tons/acre",
            f"Model confidence: {yield_result.confidence:.0%}",
            *yield_result.drivers,
            "",
            "FERTILIZER RECOMMENDATION",
            fertilizer.title,
            f"NPK correction kg/acre: N {fertilizer.npk_kg_per_acre[0]}, P {fertilizer.npk_kg_per_acre[1]}, K {fertilizer.npk_kg_per_acre[2]}",
            *fertilizer.guidance,
            "",
            "WEATHER IMPACT FORECAST",
            f"Risk score: {weather.score}/100",
            *weather.alerts,
            *weather.actions,
            "",
            "DRONE / SATELLITE MONITORING",
            f"Vegetation index: {farm.vegetation_index}",
            f"Canopy coverage: {farm.coverage_pct}%",
            f"Stress level: {farm.stress_level}",
            f"Water stress area: {farm.water_stress_pct}%",
            f"Disease-like stress area: {farm.disease_stress_pct}%",
            farm.recommendation,
        ]
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", "\n".join(lines))
        self.report.configure(state="disabled")
