"""Smart Energy Consumption Monitoring — Animated Glassmorphism Streamlit App."""

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

# ---------- Eye-Catching Animated Aurora Background & Glassmorphism CSS ----------
st.markdown(
    """
<style>
@keyframes auroraDrift {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.65); }
  50%      { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
}
@keyframes slideIn {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}

.stApp {
  background:
    radial-gradient(circle at 12% 18%, rgba(16, 185, 129, 0.22), transparent 40%),
    radial-gradient(circle at 86% 14%, rgba(56, 189, 248, 0.22), transparent 42%),
    radial-gradient(circle at 52% 88%, rgba(99, 102, 241, 0.22), transparent 48%),
    linear-gradient(135deg, #050a14 0%, #0b1326 48%, #071422 100%);
  background-size: 180% 180%;
  animation: auroraDrift 18s ease infinite;
}

/* Frosted Glass Sidebar */
section[data-testid="stSidebar"] {
  background: rgba(9, 15, 30, 0.78) !important;
  backdrop-filter: blur(18px);
  border-right: 1px solid rgba(148, 163, 184, 0.14);
}

/* Hero Banner */
.hero-box {
  position: relative;
  padding: 24px 28px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.78), rgba(16, 185, 129, 0.10) 60%, rgba(56, 189, 248, 0.14));
  border: 1px solid rgba(52, 211, 153, 0.26);
  backdrop-filter: blur(14px);
  box-shadow: 0 18px 42px rgba(2, 6, 23, 0.45);
  margin-bottom: 20px;
  animation: slideIn 0.6s ease both;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6ee7b7;
  background: rgba(16, 185, 129, 0.14);
  border: 1px solid rgba(16, 185, 129, 0.35);
  padding: 5px 12px;
  border-radius: 999px;
  margin-bottom: 10px;
}
.hero-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #34d399;
  animation: pulseGlow 1.8s infinite;
}
.hero-title {
  margin: 0;
  font-size: clamp(1.7rem, 3vw, 2.35rem);
  font-weight: 800;
  background: linear-gradient(90deg, #ffffff 0%, #6ee7b7 52%, #38bdf8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1.2;
}
.hero-sub {
  margin: 8px 0 0;
  color: #cbd5e1;
  font-size: 0.95rem;
}

/* Glowing Glass KPI Metric Cards */
div[data-testid="stMetric"] {
  background: rgba(15, 23, 42, 0.62);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  padding: 16px 18px;
  backdrop-filter: blur(14px);
  box-shadow: 0 10px 26px rgba(2, 6, 23, 0.35);
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
  animation: slideIn 0.65s ease both;
}
div[data-testid="stMetric"]:hover {
  transform: translateY(-4px);
  border-color: rgba(52, 211, 153, 0.55);
  box-shadow: 0 14px 32px rgba(16, 185, 129, 0.16);
}

/* Polished Tabs */
button[data-baseweb="tab"] {
  border-radius: 10px 10px 0 0 !important;
  font-weight: 600 !important;
  transition: color 0.2s ease, background 0.2s ease;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- Building Profile Presets ----------
PROFILES = {
    "Family House (4BR)": {"scale": 1.0, "budget": 280.0, "seed": 42},
    "Apartment (2BR)": {"scale": 0.65, "budget": 170.0, "seed": 18},
    "Small Office / Studio": {"scale": 1.55, "budget": 480.0, "seed": 77},
}

# ---------- Sidebar Controls ----------
with st.sidebar:
    st.markdown("### ⚡ Control Center")
    profile_name = st.selectbox("Building profile", list(PROFILES.keys()))
    preset = PROFILES[profile_name]

    data_source = st.radio("Data source", ["Live Simulator", "Upload CSV"], horizontal=True)
    uploaded = None
    if data_source == "Upload CSV":
        uploaded = st.file_uploader("Upload meter CSV (`timestamp`, `total_kwh`)", type=["csv"])
        days, inject_spikes, seed, ac_savings = 14, 5, preset["seed"], 0
    else:
        days = st.slider("Simulation window (days)", min_value=3, max_value=30, value=14)
        inject_spikes = st.slider("Simulated fault spikes", min_value=0, max_value=12, value=5)
        seed = st.number_input("Random seed", min_value=1, max_value=9999, value=preset["seed"], step=1)
        ac_savings = st.slider("What-If: Reduce AC usage (%)", min_value=0, max_value=40, value=0, step=5)

    st.divider()
    st.markdown("### 💳 Tariff & Budget")
    tariff_mode = st.selectbox(
        "Tariff model",
        ["TNB Tiered (MYR)", "Time-of-Use (Peak / Off-Peak)", "Custom Flat Rate"],
    )
    custom_rate = 0.45
    if tariff_mode == "Custom Flat Rate":
        custom_rate = st.number_input("Rate (RM / kWh)", min_value=0.05, max_value=2.00, value=0.45, step=0.01)
    monthly_budget = st.number_input(
        "Monthly budget target (RM)", min_value=50.0, max_value=2000.0, value=preset["budget"], step=10.0
    )

    st.divider()
    st.markdown("### 🚨 Anomaly Engine")
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
    raw_df = simulate_consumption(
        days=days,
        seed=int(seed),
        inject_anomalies=inject_spikes,
        ac_reduction_pct=float(ac_savings),
    )
    # Apply building profile load multiplier
    scale = preset["scale"]
    if scale != 1.0:
        for col in ["Air Conditioning", "Refrigerator", "Lighting", "Water Heater", "Home Office & IT", "total_kwh"]:
            raw_df[col] = (raw_df[col] * scale).round(3)

analyzed_df = detect_anomalies(raw_df, window=24, z_threshold=z_threshold)
costs = estimate_costs(analyzed_df, tariff_mode=tariff_mode, custom_rate=custom_rate)
anomalies_df = analyzed_df[analyzed_df["is_anomaly"]].copy()
night_load = phantom_overnight_load(analyzed_df)
breakdown = appliance_breakdown(analyzed_df)
profile = hourly_profile(analyzed_df)
latest_kw = float(analyzed_df["total_kwh"].iloc[-1])

# ---------- Animated Hero Header ----------
st.markdown(
    f"""
<div class="hero-box">
  <div class="hero-badge"><span class="hero-dot"></span> Live Analytics Engine · {profile_name} · Current Load: {latest_kw:.2f} kW</div>
  <h1 class="hero-title">Smart Energy Consumption Monitor</h1>
  <p class="hero-sub">
    Built by <b>Muhammad Abdullahi Bukar</b> · Real-time electricity simulation, TNB/TOU cost forecasting,
    and Pandas rolling Z-score anomaly detection powered by Streamlit &amp; Chart.js.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

# ---------- Glass KPI Cards ----------
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
    components.html(render_timeseries_chart(analyzed_df, aggregate_daily=aggregate_daily), height=375)

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Consumption by Appliance (kWh)")
        components.html(render_appliance_doughnut(breakdown), height=330)
    with col_right:
        st.subheader("24-Hour Peak Demand Profile")
        components.html(render_hourly_bar_chart(profile), height=330)

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
