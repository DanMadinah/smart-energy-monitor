"""Automated Pytest unit & integration tests for Smart Energy Consumption Monitor."""

from __future__ import annotations

import io
import pandas as pd

from src.simulator import simulate_consumption, load_uploaded_csv, APPLIANCES
from src.tariffs import calculate_tnb_tiered_cost, estimate_costs
from src.analytics import detect_anomalies, hourly_profile, appliance_breakdown, phantom_overnight_load


def test_simulator_generates_expected_rows_and_columns():
    df = simulate_consumption(days=7, seed=10, inject_anomalies=3)
    assert len(df) == 7 * 24
    for col in ["timestamp", "total_kwh", *APPLIANCES]:
        assert col in df.columns
    assert (df["total_kwh"] > 0).all()
    assert int(df["injected_fault"].sum()) == 3


def test_tnb_tiered_tariff_calculation():
    # First 200 kWh @ 0.218 = RM 43.60
    assert calculate_tnb_tiered_cost(200) == 43.60
    # 250 kWh = 200*0.218 + 50*0.334 = 43.60 + 16.70 = 60.30
    assert calculate_tnb_tiered_cost(250) == 60.30
    # Zero / negative input safely returns 0.0
    assert calculate_tnb_tiered_cost(0) == 0.0


def test_estimate_costs_across_all_tariff_modes():
    df = simulate_consumption(days=10, seed=7, inject_anomalies=0)
    tnb = estimate_costs(df, tariff_mode="TNB Tiered (MYR)")
    tou = estimate_costs(df, tariff_mode="Time-of-Use (Peak / Off-Peak)")
    flat = estimate_costs(df, tariff_mode="Custom Flat Rate", custom_rate=0.50)

    assert tnb.total_kwh > 0 and tnb.projected_30d_cost > tnb.period_cost
    assert tou.period_cost > 0
    assert abs(flat.period_cost - round(flat.total_kwh * 0.50, 2)) <= 0.05


def test_anomaly_detector_flags_injected_spikes():
    df = simulate_consumption(days=14, seed=42, inject_anomalies=5)
    analyzed = detect_anomalies(df, window=24, z_threshold=2.2)

    flagged = analyzed[analyzed["is_anomaly"]]
    assert len(flagged) >= 4
    assert set(flagged["severity"].unique()).issubset({"WARNING", "CRITICAL"})


def test_analytics_helpers_and_csv_loader():
    csv_text = (
        "timestamp,total_kwh\n"
        "2026-11-20 02:00:00,0.45\n"
        "2026-11-20 14:00:00,2.10\n"
        "2026-11-20 20:00:00,1.85\n"
    )
    df = load_uploaded_csv(io.StringIO(csv_text))
    assert len(df) == 3
    assert phantom_overnight_load(df) == 0.45
    assert len(hourly_profile(df)) == 3
    assert sum(appliance_breakdown(df).values()) > 0
