"""Pandas-based anomaly detection and energy pattern analytics."""

from __future__ import annotations

import pandas as pd
from src.simulator import APPLIANCES


def detect_anomalies(
    df: pd.DataFrame,
    window: int = 24,
    z_threshold: float = 2.5,
) -> pd.DataFrame:
    """
    Flag unusual electricity consumption using a rolling Z-score over `total_kwh`.
    Also identifies the top contributing appliance and assigns a severity level.
    """
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])

    rolling_mean = out["total_kwh"].rolling(window=window, min_periods=6).mean()
    rolling_std = out["total_kwh"].rolling(window=window, min_periods=6).std().replace(0, pd.NA)

    out["baseline_kwh"] = rolling_mean.fillna(out["total_kwh"].mean()).round(3)
    out["z_score"] = ((out["total_kwh"] - out["baseline_kwh"]) / rolling_std).fillna(0.0).round(2)
    out["is_anomaly"] = out["z_score"] >= z_threshold

    def classify(z: float) -> str:
        if z >= z_threshold + 1.2:
            return "CRITICAL"
        if z >= z_threshold:
            return "WARNING"
        return "NORMAL"

    out["severity"] = out["z_score"].apply(classify)

    # Identify highest-consuming appliance at each timestamp
    present_apps = [a for a in APPLIANCES if a in out.columns]
    if present_apps:
        out["top_appliance"] = out[present_apps].idxmax(axis=1)
    else:
        out["top_appliance"] = "Unknown"

    return out


def hourly_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Average kWh by hour of day (0–23) to expose peak demand windows."""
    tmp = df.copy()
    tmp["hour"] = pd.to_datetime(tmp["timestamp"]).dt.hour
    grouped = tmp.groupby("hour", as_index=False)["total_kwh"].mean()
    grouped["total_kwh"] = grouped["total_kwh"].round(3)
    return grouped


def appliance_breakdown(df: pd.DataFrame) -> dict[str, float]:
    """Total kWh consumed per appliance across the selected period."""
    totals: dict[str, float] = {}
    for app in APPLIANCES:
        if app in df.columns:
            totals[app] = round(float(df[app].sum()), 2)
    return totals


def phantom_overnight_load(df: pd.DataFrame) -> float:
    """Average hourly kWh between 01:00 and 05:00 (standby / phantom load indicator)."""
    hours = pd.to_datetime(df["timestamp"]).dt.hour
    night = df[(hours >= 1) & (hours <= 5)]["total_kwh"]
    if night.empty:
        return 0.0
    return round(float(night.mean()), 3)
