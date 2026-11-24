"""Electricity tariff & cost estimation engine (Malaysia TNB Tiered, TOU, and Custom)."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class CostSummary:
    total_kwh: float
    period_cost: float
    projected_30d_kwh: float
    projected_30d_cost: float
    avg_rate_per_kwh: float
    currency: str


# Malaysia TNB Residential Domestic Tiered Tariff (MYR / kWh)
TNB_TIERS: list[tuple[float, float]] = [
    (200.0, 0.218),   # First 200 kWh
    (100.0, 0.334),   # Next 100 kWh (201–300)
    (300.0, 0.516),   # Next 300 kWh (301–600)
    (300.0, 0.546),   # Next 300 kWh (601–900)
    (float("inf"), 0.571),  # Above 900 kWh
]


def calculate_tnb_tiered_cost(kwh: float) -> float:
    """Compute domestic tiered electricity bill in MYR (RM)."""
    remaining = max(0.0, float(kwh))
    total = 0.0
    for block_kwh, rate in TNB_TIERS:
        used = min(remaining, block_kwh)
        total += used * rate
        remaining -= used
        if remaining <= 0:
            break
    return round(total, 2)


def estimate_costs(
    df: pd.DataFrame,
    tariff_mode: str = "TNB Tiered (MYR)",
    custom_rate: float = 0.45,
    peak_rate: float = 0.62,
    offpeak_rate: float = 0.28,
) -> CostSummary:
    """Calculate actual period cost and 30-day projected electricity bill."""
    if df.empty:
        return CostSummary(0.0, 0.0, 0.0, 0.0, 0.0, "RM")

    total_kwh = float(df["total_kwh"].sum())
    span_hours = max(1.0, float(len(df)))
    projected_30d_kwh = total_kwh * (720.0 / span_hours)

    if tariff_mode == "TNB Tiered (MYR)":
        period_cost = calculate_tnb_tiered_cost(total_kwh)
        projected_30d_cost = calculate_tnb_tiered_cost(projected_30d_kwh)
        currency = "RM"
    elif tariff_mode == "Time-of-Use (Peak / Off-Peak)":
        hours = pd.to_datetime(df["timestamp"]).dt.hour
        is_peak = (hours >= 14) & (hours <= 22)
        rates = is_peak.map({True: peak_rate, False: offpeak_rate})
        period_cost = round(float((df["total_kwh"] * rates).sum()), 2)
        projected_30d_cost = round(period_cost * (720.0 / span_hours), 2)
        currency = "RM"
    else:
        period_cost = round(total_kwh * custom_rate, 2)
        projected_30d_cost = round(projected_30d_kwh * custom_rate, 2)
        currency = "RM"

    avg_rate = round(period_cost / total_kwh, 3) if total_kwh > 0 else 0.0
    return CostSummary(
        total_kwh=round(total_kwh, 2),
        period_cost=period_cost,
        projected_30d_kwh=round(projected_30d_kwh, 1),
        projected_30d_cost=projected_30d_cost,
        avg_rate_per_kwh=avg_rate,
        currency=currency,
    )
