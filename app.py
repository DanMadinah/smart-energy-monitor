"""Smart Energy Consumption Monitoring — Streamlit + Pandas + Chart.js App."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from src.simulator import simulate_consumption, load_uploaded_csv
from src.tariffs import estimate_costs
from src.analytics import (
    detect_anomalies,
    hourly_profile,
    appliance_breakdown,
    phantom_overnight_load,
)
from src.charts import (
    render_timeseries_chart,
    render_appliance_doughnut,
    render_hourly_bar_chart,
)

st.set_page_config(
    page_title="Smart Energy Consumption Monitor — Muhammad Abdullahi Bukar",
    page_icon="⚡",
    layout="wide",
)

# ---------- Header ----------
st.title("⚡ Smart Energy Consumption Monitor")
st.caption(
    "By **Muhammad Abdullahi Bukar** · Software-only electricity simulator, cost estimator, "
    "and statistical anomaly detector built with Python, Streamlit, Pandas & Chart.js."
)

# ---------- Sidebar Controls ----------
with st.sidebar:
    st.header("Simulation & Data Source")
    data_source = st.radio("Source", ["Live Simulator", "Upload CSV"], horizontal=True)

    uploaded = None
    if data_source == "Upload CSV":
        uploaded = st.file_uploader("Upload meter CSV (`timestamp`, `total_kwh`)", type=["csv"])
    else:
        days = st.slider("Simulation window (days)", min_value=3, max_value=30, value=14)
        inject_spikes = st.slider("Simulated fault spikes", min_value=0, max_value=12, value=5)
        seed = st.number_input("Random seed", min_value=1, max_value=9999, value=42, step=1)
        ac_savings = st.slider("What-If: Reduce AC usage (%)", min_value=0, max_value=40, value=0, step=5)

    st.divider()
    st.header("Tariff & Budget")
    tariff_mode = st.selectbox(
        "Tariff model",
        ["TNB Tiered (MYR)", "Time-of-Use (Peak / Off-Peak)", "Custom Flat Rate"],
    )
    custom_rate = 0.45
    if tariff_mode == "Custom Flat Rate":
        custom_rate = st.number_input("Rate (RM / kWh)", min_value=0.05, max_value=2.00, value=0.45, step=0.01)
    monthly_budget = st.number_input("Monthly budget target (RM)", min_value=50.0, max_value=2000.0, value=250.0, step=10.0)

    st.divider()
    st.header("Anomaly Detection")
    z_threshold = st.slider("Rolling Z-score threshold", min_value=1.5, max_value=4.0, value=2.5, step=0.1)
    aggregate_daily = st.toggle("Aggregate chart by day", value=False)

# ---------- Load / Simulate Data ----------
if data_source == "Upload CSV" and uploaded is not None:
    try:
        raw_df = load_uploaded_csv(uploaded)
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
        st.stop()
else:
    if data_source == "Upload CSV":
        st.info("Upload a CSV with `timestamp` and `total_kwh` columns — showing simulated data in the meantime.")
        raw_df = simulate_consumption(days=14, seed=42, inject_anomalies=5)
    else:
        raw_df = simulate_consumption(
            days=days,
            seed=int(seed),
            inject_anomalies=inject_spikes,
            ac_reduction_pct=float(ac_savings),
        )

analyzed_df = detect_anomalies(raw_df, window=24, z_threshold=z_threshold)
costs = estimate_costs(analyzed_df, tariff_mode=tariff_mode, custom_rate=custom_rate)
anomalies_df = analyzed_df[analyzed_df["is_anomaly"]].copy()
night_load = phantom_overnight_load(analyzed_df)
breakdown = appliance_breakdown(analyzed_df)
profile = hourly_profile(analyzed_df)

# ---------- KPI Cards ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Energy Used", f"{costs.total_kwh:,.2f} kWh", f"Avg {costs.avg_rate_per_kwh:.3f} {costs.currency}/kWh")
c2.metric("Estimated Period Cost", f"{costs.currency} {costs.period_cost:,.2f}", tariff_mode.split(" ")[0])
budget_delta = costs.projected_30d_cost - monthly_budget
c3.metric(
    "Projected 30-Day Bill",
    f"{costs.currency} {costs.projected_30d_cost:,.2f}",
    f"{budget_delta:+.2f} {costs.currency} vs budget",
    delta_color="inverse",
)
c4.metric(
    "Unusual Spikes Flagged",
    f"{len(anomalies_df)}",
    f"Overnight base: {night_load:.2f} kWh/h",
    delta_color="off",
)

# Budget progress bar
budget_ratio = min(1.0, costs.projected_30d_cost / max(1.0, monthly_budget))
if costs.projected_30d_cost > monthly_budget:
    st.warning(
        f"Projected 30-day bill (**{costs.currency} {costs.projected_30d_cost:,.2f}**) exceeds your "
        f"**{costs.currency} {monthly_budget:,.2f}** monthly budget. Try adjusting the *What-If AC Reduction* slider in the sidebar."
    )
st.progress(budget_ratio, text=f"Monthly Budget Utilization: {int((costs.projected_30d_cost / max(1.0, monthly_budget)) * 100)}%")

# ---------- Tabs ----------
tab_overview, tab_anomalies, tab_data = st.tabs(
    ["📈 Monitoring & Charts (Chart.js)", f"🚨 Anomaly Alerts ({len(anomalies_df)})", "📄 Data & Export"]
)

with tab_overview:
    st.subheader("Energy Consumption Over Time (with Rolling Baseline & Anomalies)")
    components.html(render_timeseries_chart(analyzed_df, aggregate_daily=aggregate_daily), height=360)

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Consumption by Appliance (kWh)")
        components.html(render_appliance_doughnut(breakdown), height=310)
    with col_right:
        st.subheader("24-Hour Peak Demand Profile")
        components.html(render_hourly_bar_chart(profile), height=310)

with tab_anomalies:
    st.subheader("Detected Unusual Consumption Patterns")
    st.caption(
        f"Flagged automatically using a 24-hour rolling Z-score ≥ **{z_threshold:.1f}** "
        "(identifies power surges, stuck compressors, or abnormal heater loads)."
    )
    if anomalies_df.empty:
        st.success("No unusual consumption spikes detected at the current sensitivity threshold.")
    else:
        display_cols = ["timestamp", "total_kwh", "baseline_kwh", "z_score", "severity", "top_appliance"]
        st.dataframe(
            anomalies_df[display_cols].sort_values("timestamp", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

with tab_data:
    st.subheader("Raw & Analyzed Meter Readings")
    st.dataframe(analyzed_df.tail(200), use_container_width=True, hide_index=True)

    csv_bytes = analyzed_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Full Analyzed Report (CSV)",
        data=csv_bytes,
        file_name="smart-energy-report.csv",
        mime="text/csv",
    )
