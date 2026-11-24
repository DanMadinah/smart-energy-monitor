"""PDF summary report generator using fpdf2."""

from __future__ import annotations

from datetime import datetime
import pandas as pd
from fpdf import FPDF

from src.tariffs import CostSummary
from src.analytics import CarbonEstimate


def _safe(text: str) -> str:
    """Keep text strictly Latin-1 safe for built-in PDF Helvetica font."""
    return (
        text.replace("—", "-")
        .replace("–", "-")
        .replace("₂", "2")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def build_pdf_report(
    profile_name: str,
    data_mode: str,
    tariff_mode: str,
    costs: CostSummary,
    carbon: CarbonEstimate,
    appliance_df: pd.DataFrame,
    anomalies_df: pd.DataFrame,
) -> bytes:
    """Build a clean downloadable PDF energy summary report."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _safe("Smart Energy Monitor - Usage Report"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(
        0,
        6,
        _safe(
            f"Author: Muhammad Abdullahi Bukar | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"Source: {data_mode} ({profile_name})"
        ),
        ln=True,
    )
    pdf.ln(4)

    # Summary KPIs
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "1. Usage & Bill Summary (Estimate)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    summary_lines = [
        f"Tariff Mode: {tariff_mode}",
        f"Measured Span: {costs.span_hours:.1f} hours | Total Energy: {costs.total_kwh:,.2f} kWh",
        f"Average Power: {costs.avg_power_kw:.3f} kW | Effective Rate: {costs.currency} {costs.avg_rate_per_kwh:.3f}/kWh",
        f"Estimated Period Cost: {costs.currency} {costs.period_cost:,.2f}",
        f"Projected 30-Day Usage: {costs.projected_30d_kwh:,.1f} kWh -> Est. Monthly Bill: {costs.currency} {costs.projected_30d_cost:,.2f}",
        f"Estimated CO2 Emissions: {carbon.period_co2_kg:,.2f} kg (Monthly est: {carbon.projected_30d_co2_kg:,.2f} kg CO2e @ {carbon.factor_kg_per_kwh} kg/kWh)",
    ]
    for line in summary_lines:
        pdf.cell(0, 6, _safe(line), ln=True)

    if costs.breakdown:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Projected Monthly Bill Breakdown:", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for label, amount in costs.breakdown.items():
            pdf.cell(0, 6, _safe(f"  - {label}: {costs.currency} {amount:,.2f}"), ln=True)

    # Appliance Breakdown
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "2. Consumption by Appliance", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for row in appliance_df.itertuples():
        line = (
            f"  - {row.Appliance}: {getattr(row, '_2'):,.2f} kWh "
            f"({getattr(row, '_3'):.1f}%) | Est. {costs.currency} {getattr(row, '_5'):,.2f}"
        )
        pdf.cell(0, 6, _safe(line), ln=True)

    # Unusual Spikes
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"3. Unusual Power Spikes ({len(anomalies_df)} flagged)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    if anomalies_df.empty:
        pdf.cell(0, 6, "No unusual consumption spikes detected.", ln=True)
    else:
        for row in anomalies_df.sort_values("timestamp", ascending=False).head(12).itertuples():
            ts_str = pd.to_datetime(row.timestamp).strftime("%Y-%m-%d %H:%M")
            pdf.cell(0, 6, _safe(f"  - [{row.severity}] {ts_str}: {row.reason}"), ln=True)

    return bytes(pdf.output())
