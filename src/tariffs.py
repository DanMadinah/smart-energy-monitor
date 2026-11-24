"""Electricity tariff & cost estimator (Malaysia July 2025–2027 structure, TOU, and Custom)."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class TariffRates2025:
    """
    Configurable Malaysia domestic tariff components (effective 1 July 2025 – 31 Dec 2027).
    Values are defaults for estimation and can be adjusted in the sidebar.
    """
    energy_standard: float = 0.2703   # RM/kWh (<= 1,500 kWh/month)
    energy_high: float = 0.3703       # RM/kWh (> 1,500 kWh/month)
    capacity_rate: float = 0.0455     # RM/kWh
    network_rate: float = 0.1285      # RM/kWh
    afa_rate: float = 0.0000          # Automatic Fuel Adjustment (RM/kWh, can be +/-)
    retail_monthly: float = 10.00     # RM/month (waived when monthly usage <= 600 kWh)
    retail_waiver_kwh: float = 600.0
    high_tier_threshold_kwh: float = 1500.0


@dataclass(frozen=True)
class CostSummary:
    total_kwh: float
    period_cost: float
    projected_30d_kwh: float
    projected_30d_cost: float
    avg_rate_per_kwh: float
    avg_power_kw: float
    span_hours: float
    currency: str
    breakdown: dict[str, float]


def calculate_malaysia_2025_bill(
    kwh: float,
    rates: TariffRates2025 | None = None,
    apply_monthly_retail: bool = True,
) -> tuple[float, dict[str, float]]:
    """
    Estimate a residential bill in MYR using the July 2025–2027 component structure:
    Energy + Capacity + Network + AFA + Retail Charge (waived <= 600 kWh).
    """
    r = rates or TariffRates2025()
    usage = max(0.0, float(kwh))

    if usage <= r.high_tier_threshold_kwh:
        energy_cost = usage * r.energy_standard
    else:
        energy_cost = (
            r.high_tier_threshold_kwh * r.energy_standard
            + (usage - r.high_tier_threshold_kwh) * r.energy_high
        )

    capacity_cost = usage * r.capacity_rate
    network_cost = usage * r.network_rate
    afa_cost = usage * r.afa_rate
    retail_cost = r.retail_monthly if (apply_monthly_retail and usage > r.retail_waiver_kwh) else 0.0

    total = max(0.0, energy_cost + capacity_cost + network_cost + afa_cost + retail_cost)
    parts = {
        "Energy Charge": round(energy_cost, 2),
        "Capacity Charge": round(capacity_cost, 2),
        "Network Charge": round(network_cost, 2),
        "AFA Adjustment": round(afa_cost, 2),
        "Retail Charge": round(retail_cost, 2),
    }
    return round(total, 2), parts


def compute_elapsed_hours(df: pd.DataFrame) -> float:
    """
    Calculate true elapsed time span in hours from timestamps (handles irregular intervals).
    Falls back to row count if fewer than 2 distinct timestamps exist.
    """
    if df.empty:
        return 0.0
    ts = pd.to_datetime(df["timestamp"]).sort_values()
    if len(ts) < 2:
        return 1.0
    diffs = ts.diff().dropna().dt.total_seconds() / 3600.0
    median_step = float(diffs.median()) if not diffs.empty and float(diffs.median()) > 0 else 1.0
    elapsed = (ts.iloc[-1] - ts.iloc[0]).total_seconds() / 3600.0 + median_step
    return max(1.0, elapsed)


def estimate_costs(
    df: pd.DataFrame,
    tariff_mode: str = "Malaysia 2025–2027 Estimate (MYR)",
    rates_2025: TariffRates2025 | None = None,
    custom_rate: float = 0.45,
    peak_rate: float = 0.62,
    offpeak_rate: float = 0.28,
) -> CostSummary:
    """Calculate actual period cost, 30-day projection, and average power (kW)."""
    if df.empty:
        return CostSummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "RM", {})

    total_kwh = float(df["total_kwh"].sum())
    span_hours = compute_elapsed_hours(df)
    avg_power_kw = round(total_kwh / span_hours, 3) if span_hours > 0 else 0.0
    projected_30d_kwh = total_kwh * (720.0 / span_hours)

    if tariff_mode == "Malaysia 2025–2027 Estimate (MYR)":
        period_cost, _ = calculate_malaysia_2025_bill(total_kwh, rates=rates_2025, apply_monthly_retail=False)
        projected_30d_cost, breakdown = calculate_malaysia_2025_bill(
            projected_30d_kwh, rates=rates_2025, apply_monthly_retail=True
        )
    elif tariff_mode == "Time-of-Use (Peak / Off-Peak)":
        hours = pd.to_datetime(df["timestamp"]).dt.hour
        is_peak = (hours >= 14) & (hours <= 22)
        rates = is_peak.map({True: peak_rate, False: offpeak_rate})
        period_cost = round(float((df["total_kwh"] * rates).sum()), 2)
        projected_30d_cost = round(period_cost * (720.0 / span_hours), 2)
        peak_kwh = float(df.loc[is_peak, "total_kwh"].sum())
        off_kwh = total_kwh - peak_kwh
        breakdown = {
            "Peak Usage Cost": round(peak_kwh * peak_rate, 2),
            "Off-Peak Usage Cost": round(off_kwh * offpeak_rate, 2),
        }
    else:
        period_cost = round(total_kwh * custom_rate, 2)
        projected_30d_cost = round(projected_30d_kwh * custom_rate, 2)
        breakdown = {"Flat Rate Energy": projected_30d_cost}

    avg_rate = round(period_cost / total_kwh, 3) if total_kwh > 0 else 0.0
    return CostSummary(
        total_kwh=round(total_kwh, 2),
        period_cost=period_cost,
        projected_30d_kwh=round(projected_30d_kwh, 1),
        projected_30d_cost=projected_30d_cost,
        avg_rate_per_kwh=avg_rate,
        avg_power_kw=avg_power_kw,
        span_hours=round(span_hours, 1),
        currency="RM",
        breakdown=breakdown,
    )
