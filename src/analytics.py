"""Pandas anomaly detection (shifted baseline), carbon estimator, forecasting, and appliance stats."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import numpy as np
import pandas as pd
from src.simulator import APPLIANCES

# Peninsular Malaysia grid emission factor reference (kg CO2e per kWh, Energy Commission / MGTC)
DEFAULT_CO2_KG_PER_KWH = 0.585


@dataclass(frozen=True)
class CarbonEstimate:
    period_co2_kg: float
    projected_30d_co2_kg: float
    trees_needed_monthly: float
    factor_kg_per_kwh: float


def detect_anomalies(
    df: pd.DataFrame,
    window: int = 24,
    z_threshold: float = 2.5,
) -> pd.DataFrame:
    """
    Flag unusual electricity spikes using a shifted rolling Z-score.
    Using `.shift(1)` ensures the current reading never biases its own baseline.
    """
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])

    prior = out["total_kwh"].shift(1)
    rolling_mean = prior.rolling(window=window, min_periods=6).mean()
    rolling_std = prior.rolling(window=window, min_periods=6).std().replace(0, pd.NA)

    fallback_mean = float(out["total_kwh"].mean()) if not out.empty else 0.0
    out["baseline_kwh"] = rolling_mean.fillna(fallback_mean).round(3)
    out["z_score"] = ((out["total_kwh"] - out["baseline_kwh"]) / rolling_std).fillna(0.0).round(2)
    out["is_anomaly"] = out["z_score"] >= z_threshold

    def classify(z: float) -> str:
        if z >= z_threshold + 1.2:
            return "CRITICAL"
        if z >= z_threshold:
            return "WARNING"
        return "NORMAL"

    out["severity"] = out["z_score"].apply(classify)

    present_apps = [a for a in APPLIANCES if a in out.columns]
    if present_apps:
        out["top_appliance"] = out[present_apps].idxmax(axis=1)
    else:
        out["top_appliance"] = "Unknown"

    def explain(row: pd.Series) -> str:
        if not row["is_anomaly"]:
            return "Within normal range"
        base = float(row["baseline_kwh"])
        actual = float(row["total_kwh"])
        ratio = (actual / base) if base > 0 else 1.0
        return f"{ratio:.1f}x normal ({actual:.2f} vs {base:.2f} kWh) — mostly {row['top_appliance']}"

    out["reason"] = out.apply(explain, axis=1)
    return out


def hourly_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Average kWh by hour of day (0–23)."""
    tmp = df.copy()
    tmp["hour"] = pd.to_datetime(tmp["timestamp"]).dt.hour
    grouped = tmp.groupby("hour", as_index=False)["total_kwh"].mean()
    grouped["total_kwh"] = grouped["total_kwh"].round(3)
    return grouped


def appliance_breakdown(df: pd.DataFrame) -> dict[str, float]:
    """Total kWh per appliance across the selected period."""
    totals: dict[str, float] = {}
    for app in APPLIANCES:
        if app in df.columns:
            totals[app] = round(float(df[app].sum()), 2)
    return totals


def appliance_summary_table(df: pd.DataFrame, avg_rate_rm: float) -> pd.DataFrame:
    """Per-appliance kWh, percentage share, average hourly kWh, and estimated RM cost."""
    totals = appliance_breakdown(df)
    grand_total = sum(totals.values())
    rows = []
    for app, kwh in totals.items():
        pct = round((kwh / grand_total) * 100.0, 1) if grand_total > 0 else 0.0
        avg_hr = round(float(df[app].mean()), 3) if app in df.columns and not df.empty else 0.0
        est_cost = round(kwh * avg_rate_rm, 2)
        rows.append(
            {
                "Appliance": app,
                "Total (kWh)": kwh,
                "Share (%)": pct,
                "Avg per Hour (kWh)": avg_hr,
                "Est. Cost (RM)": est_cost,
            }
        )
    return pd.DataFrame(rows).sort_values("Total (kWh)", ascending=False).reset_index(drop=True)


def phantom_overnight_load(df: pd.DataFrame) -> float:
    """Average hourly kWh between 01:00 and 05:00."""
    hours = pd.to_datetime(df["timestamp"]).dt.hour
    night = df[(hours >= 1) & (hours <= 5)]["total_kwh"]
    if night.empty:
        return 0.0
    return round(float(night.mean()), 3)


def estimate_carbon_emissions(
    period_kwh: float,
    projected_30d_kwh: float,
    factor_kg_per_kwh: float = DEFAULT_CO2_KG_PER_KWH,
) -> CarbonEstimate:
    """Estimate CO2e emissions using a documented grid emission factor."""
    period_co2 = round(max(0.0, period_kwh) * factor_kg_per_kwh, 2)
    monthly_co2 = round(max(0.0, projected_30d_kwh) * factor_kg_per_kwh, 2)
    # One mature tree absorbs ~1.8 kg CO2 per month (~21.6 kg/year)
    trees = round(monthly_co2 / 1.8, 1) if monthly_co2 > 0 else 0.0
    return CarbonEstimate(
        period_co2_kg=period_co2,
        projected_30d_co2_kg=monthly_co2,
        trees_needed_monthly=trees,
        factor_kg_per_kwh=factor_kg_per_kwh,
    )


def forecast_next_7_days(df: pd.DataFrame) -> pd.DataFrame:
    """
    Forecast the next 7 days of daily energy consumption (kWh) using historical
    daily totals and a damped linear trend (explainable baseline model).
    """
    if df.empty:
        return pd.DataFrame(columns=["date", "predicted_kwh"])

    tmp = df.copy()
    tmp["timestamp"] = pd.to_datetime(tmp["timestamp"])
    daily = tmp.set_index("timestamp").resample("D")["total_kwh"].sum()
    daily = daily[daily > 0]
    if daily.empty:
        return pd.DataFrame(columns=["date", "predicted_kwh"])

    y = daily.values.astype(float)
    base_mean = float(np.mean(y))
    slope = 0.0
    if len(y) >= 3:
        x = np.arange(len(y), dtype=float)
        raw_slope = float(np.polyfit(x, y, 1)[0])
        # Damp slope to prevent unrealistic runaway projections on short windows
        slope = float(np.clip(raw_slope * 0.4, -base_mean * 0.03, base_mean * 0.03))

    last_date = daily.index[-1]
    rows = []
    for step in range(1, 8):
        next_day = last_date + timedelta(days=step)
        weekend_bump = 1.05 if next_day.weekday() >= 5 else 0.98
        pred = max(0.5, (base_mean + slope * step) * weekend_bump)
        rows.append({"date": next_day.strftime("%Y-%m-%d"), "predicted_kwh": round(pred, 2)})

    return pd.DataFrame(rows)
