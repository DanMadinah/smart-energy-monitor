"""Automated Pytest unit & integration tests for Smart Energy Monitor."""

from __future__ import annotations

import io
import pandas as pd

from src.simulator import simulate_consumption, load_uploaded_csv, APPLIANCES
from src.tariffs import TariffRates2025, calculate_malaysia_2025_bill, estimate_costs
from src.analytics import (
    detect_anomalies,
    hourly_profile,
    appliance_breakdown,
    appliance_summary_table,
    phantom_overnight_load,
    estimate_carbon_emissions,
    forecast_next_7_days,
)
from src.mqtt_sim import build_mqtt_messages
from src.report import build_pdf_report


def test_simulator_generates_expected_rows_and_columns():
    df = simulate_consumption(days=7, seed=10, inject_anomalies=3)
    assert len(df) == 7 * 24
    for col in ["timestamp", "total_kwh", *APPLIANCES]:
        assert col in df.columns
    assert (df["total_kwh"] > 0).all()
    assert int(df["injected_fault"].sum()) == 3


def test_malaysia_2025_tariff_calculation_and_retail_waiver():
    rates = TariffRates2025()
    # Under 600 kWh: monthly retail charge is waived
    cost_500, parts_500 = calculate_malaysia_2025_bill(500, rates=rates, apply_monthly_retail=True)
    assert parts_500["Retail Charge"] == 0.0
    assert cost_500 == round(500 * (0.2703 + 0.0455 + 0.1285), 2)

    # Above 600 kWh: RM 10 monthly retail charge applies
    cost_700, parts_700 = calculate_malaysia_2025_bill(700, rates=rates, apply_monthly_retail=True)
    assert parts_700["Retail Charge"] == 10.0
    assert cost_700 == round(700 * (0.2703 + 0.0455 + 0.1285) + 10.0, 2)


def test_estimate_costs_across_all_tariff_modes():
    df = simulate_consumption(days=10, seed=7, inject_anomalies=0)
    my25 = estimate_costs(df, tariff_mode="Malaysia 2025–2027 Estimate (MYR)")
    tou = estimate_costs(df, tariff_mode="Time-of-Use (Peak / Off-Peak)")
    flat = estimate_costs(df, tariff_mode="Custom Flat Rate", custom_rate=0.50)

    assert my25.total_kwh > 0 and my25.avg_power_kw > 0
    assert my25.projected_30d_cost > my25.period_cost
    assert tou.period_cost > 0
    assert abs(flat.period_cost - round(flat.total_kwh * 0.50, 2)) <= 0.05


def test_shifted_anomaly_detector_flags_spike_without_self_bias():
    # Flat 1.0 kWh series with one sharp 4.0 kWh spike at index 24
    ts = pd.date_range("2026-11-01", periods=30, freq="h")
    vals = [1.0 + (0.05 if i % 2 == 0 else -0.05) for i in range(30)]
    vals[24] = 4.0
    df = pd.DataFrame(
        {
            "timestamp": ts,
            "Air Conditioning": vals,
            "Refrigerator": [0.1] * 30,
            "Lighting": [0.1] * 30,
            "Water Heater": [0.1] * 30,
            "Home Office & IT": [0.1] * 30,
            "total_kwh": vals,
        }
    )
    analyzed = detect_anomalies(df, window=24, z_threshold=2.5)
    assert bool(analyzed.loc[24, "is_anomaly"]) is True
    # Baseline at index 24 must be calculated from prior rows only (~1.0), not pulled up by 4.0
    assert abs(float(analyzed.loc[24, "baseline_kwh"]) - 1.0) < 0.1


def test_csv_validation_catches_bad_rows_duplicates_negatives_and_gaps():
    csv_text = (
        "timestamp,total_kwh\n"
        "not-a-date,1.20\n"
        "2026-11-20 01:00:00,0.50\n"
        "2026-11-20 02:00:00,abc\n"
        "2026-11-20 02:00:00,-1.50\n"
        "2026-11-20 02:00:00,0.60\n"
        "2026-11-20 02:00:00,0.65\n"
        "2026-11-20 03:00:00,0.70\n"
        "2026-11-20 09:00:00,1.90\n"
    )
    df, report = load_uploaded_csv(io.StringIO(csv_text))
    assert report.invalid_timestamps_dropped == 1
    assert report.missing_values_dropped == 1
    assert report.negative_values_rejected == 1
    assert report.duplicate_timestamps_merged == 1
    assert report.irregular_intervals_found >= 1
    assert len(df) == 4
    assert phantom_overnight_load(df) > 0
    assert len(hourly_profile(df)) == 4
    assert sum(appliance_breakdown(df).values()) > 0


def test_carbon_forecast_mqtt_and_pdf_report():
    df = detect_anomalies(simulate_consumption(days=7, seed=42, inject_anomalies=3), window=24, z_threshold=2.5)
    costs = estimate_costs(df)
    carbon = estimate_carbon_emissions(costs.total_kwh, costs.projected_30d_kwh)
    assert carbon.projected_30d_co2_kg > carbon.period_co2_kg > 0

    fc = forecast_next_7_days(df)
    assert len(fc) == 7
    assert (fc["predicted_kwh"] > 0).all()

    mqtt_msgs = build_mqtt_messages(df, profile_slug="family-house", limit=4)
    assert len(mqtt_msgs) >= 4
    assert mqtt_msgs[0]["Topic"].startswith("home/family-house/")

    app_table = appliance_summary_table(df, avg_rate_rm=costs.avg_rate_per_kwh)
    pdf_bytes = build_pdf_report(
        profile_name="Family House (4BR)",
        data_mode="Simulated Data",
        tariff_mode="Malaysia 2025–2027 Estimate (MYR)",
        costs=costs,
        carbon=carbon,
        appliance_df=app_table,
        anomalies_df=df[df["is_anomaly"]],
    )
    assert pdf_bytes.startswith(b"%PDF")
