"""Smart Energy Consumption Monitoring — Animated Glassmorphism Streamlit App."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from src.simulator import simulate_consumption, load_uploaded_csv, APPLIANCES
from src.tariffs import TariffRates2025, estimate_costs
from src.analytics import (
    DEFAULT_CO2_KG_PER_KWH,
    detect_anomalies,
    hourly_profile,
    appliance_breakdown,
    appliance_summary_table,
    phantom_overnight_load,
    estimate_carbon_emissions,
    forecast_next_7_days,
)
from src.charts import (
    render_timeseries_chart,
    render_appliance_doughnut,
    render_hourly_bar_chart,
)
from src.mqtt_sim import build_mqtt_messages
from src.report import build_pdf_report

st.set_page_config(
    page_title="Smart Energy Consumption Monitor — Muhammad Abdullahi Bukar",
    page_icon="⚡",
    layout="wide",
)

# ---------- Eye-Catching Animated Energy Background & Glassmorphism CSS ----------
st.markdown(
    """
<style>
@keyframes auroraDrift {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  50%      { box-shadow: 0 0 0 9px rgba(16, 185, 129, 0); }
}
@keyframes slideIn {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes floatUp {
  0%   { transform: translateY(105vh) rotate(0deg) scale(0.85); opacity: 0; }
  12%  { opacity: 0.32; }
  85%  { opacity: 0.28; }
  100% { transform: translateY(-15vh) rotate(18deg) scale(1.1); opacity: 0; }
}
@keyframes shootRight {
  0%   { transform: translateX(-180px); opacity: 0; }
  15%  { opacity: 0.9; }
  85%  { opacity: 0.9; }
  100% { transform: translateX(115vw); opacity: 0; }
}
@keyframes spinSlow {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(45px, -55px) scale(1.15); }
}
@keyframes cableFlow {
  to { stroke-dashoffset: -48; }
}
@keyframes waveScroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}

.stApp {
  background:
    radial-gradient(circle at 12% 18%, rgba(16, 185, 129, 0.18), transparent 40%),
    radial-gradient(circle at 86% 14%, rgba(56, 189, 248, 0.20), transparent 42%),
    radial-gradient(circle at 52% 88%, rgba(99, 102, 241, 0.20), transparent 48%),
    linear-gradient(135deg, #040812 0%, #091224 50%, #061320 100%);
  background-size: 180% 180%;
  animation: auroraDrift 18s ease infinite;
}

/* Full-screen animated energy background layer */
#energy-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}
.e-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(56, 189, 248, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(16, 185, 129, 0.045) 1px, transparent 1px);
  background-size: 64px 64px;
}
.e-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(42px);
  opacity: 0.28;
  animation: orbFloat 16s ease-in-out infinite;
}
.e-orb.o1 { width: 320px; height: 320px; left: -60px; top: 12%; background: #10b981; animation-duration: 18s; }
.e-orb.o2 { width: 280px; height: 280px; right: -40px; top: 30%; background: #38bdf8; animation-duration: 22s; animation-delay: -6s; }
.e-orb.o3 { width: 340px; height: 340px; left: 32%; bottom: -80px; background: #6366f1; animation-duration: 25s; animation-delay: -11s; }

/* Shooting power pulses along horizontal circuit tracks */
.e-pulse {
  position: absolute;
  left: 0;
  height: 2px;
  width: 150px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, #34d399, #38bdf8, transparent);
  box-shadow: 0 0 12px #34d399;
  animation: shootRight linear infinite;
}
.e-pulse.p1 { top: 18%; animation-duration: 7s; }
.e-pulse.p2 { top: 47%; animation-duration: 10s; animation-delay: -3.5s; background: linear-gradient(90deg, transparent, #f59e0b, #fde047, transparent); box-shadow: 0 0 12px #f59e0b; }
.e-pulse.p3 { top: 74%; animation-duration: 8.5s; animation-delay: -6s; }

/* Floating energy icons */
.e-icon {
  position: absolute;
  bottom: -60px;
  opacity: 0;
  animation: floatUp linear infinite;
}
.e-icon.i1 { left: 8%;  animation-duration: 15s; animation-delay: -2s; }
.e-icon.i2 { left: 24%; animation-duration: 21s; animation-delay: -9s; }
.e-icon.i3 { left: 46%; animation-duration: 18s; animation-delay: -5s; }
.e-icon.i4 { left: 68%; animation-duration: 23s; animation-delay: -13s; }
.e-icon.i5 { left: 86%; animation-duration: 17s; animation-delay: -7s; }

.e-spin {
  transform-box: fill-box;
  transform-origin: center;
  animation: spinSlow 6s linear infinite;
}

/* Bottom scrolling AC sine wave strip */
.e-wave-wrap {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  height: 54px;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  opacity: 0.35;
}
.e-wave-track {
  display: flex;
  width: 200%;
  height: 100%;
  animation: waveScroll 9s linear infinite;
}

/* Keep main Streamlit content crisp above background */
.stMainBlockContainer, section[data-testid="stSidebar"] {
  position: relative;
  z-index: 1;
}

/* Frosted Glass Sidebar */
section[data-testid="stSidebar"] {
  background: rgba(8, 13, 27, 0.82) !important;
  backdrop-filter: blur(18px);
  border-right: 1px solid rgba(148, 163, 184, 0.14);
}

/* Hero Banner + Animated Smart Grid Scene */
.hero-box {
  position: relative;
  padding: 22px 26px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.80), rgba(16, 185, 129, 0.10) 60%, rgba(56, 189, 248, 0.14));
  border: 1px solid rgba(52, 211, 153, 0.28);
  backdrop-filter: blur(14px);
  box-shadow: 0 18px 42px rgba(2, 6, 23, 0.48);
  margin-bottom: 20px;
  animation: slideIn 0.6s ease both;
}
.hero-grid {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 18px;
  align-items: center;
}
@media (max-width: 900px) {
  .hero-grid { grid-template-columns: 1fr; }
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
  font-size: clamp(1.65rem, 2.8vw, 2.25rem);
  font-weight: 800;
  background: linear-gradient(90deg, #ffffff 0%, #6ee7b7 52%, #38bdf8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1.2;
}
.hero-sub {
  margin: 8px 0 0;
  color: #cbd5e1;
  font-size: 0.93rem;
}
.flow-line {
  stroke-dasharray: 12 12;
  animation: cableFlow 1.1s linear infinite;
}
.flow-line-amber {
  stroke-dasharray: 10 14;
  animation: cableFlow 1.4s linear infinite;
}

/* Glowing Glass KPI Metric Cards */
div[data-testid="stMetric"] {
  background: rgba(15, 23, 42, 0.66);
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
  box-shadow: 0 14px 32px rgba(16, 185, 129, 0.18);
}

button[data-baseweb="tab"] {
  border-radius: 10px 10px 0 0 !important;
  font-weight: 600 !important;
}
</style>

<div id="energy-bg" aria-hidden="true">
  <div class="e-grid"></div>
  <div class="e-orb o1"></div>
  <div class="e-orb o2"></div>
  <div class="e-orb o3"></div>
  <div class="e-pulse p1"></div>
  <div class="e-pulse p2"></div>
  <div class="e-pulse p3"></div>
  <!-- Floating Lightning Bolt -->
  <svg class="e-icon i1" width="38" height="38" viewBox="0 0 24 24" fill="#34d399">
    <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z"/>
  </svg>
  <!-- Floating Spinning Wind Turbine -->
  <svg class="e-icon i2" width="46" height="46" viewBox="0 0 48 48" fill="none">
    <g class="e-spin" stroke="#38bdf8" stroke-width="2.6" stroke-linecap="round">
      <line x1="24" y1="24" x2="24" y2="6"/>
      <line x1="24" y1="24" x2="39" y2="33"/>
      <line x1="24" y1="24" x2="9" y2="33"/>
    </g>
    <circle cx="24" cy="24" r="3.5" fill="#e0f2fe"/>
  </svg>
  <!-- Floating Solar Pulse -->
  <svg class="e-icon i3" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2">
    <circle cx="12" cy="12" r="4" fill="#fbbf24"/>
    <path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1L7 17M17 7l2.1-2.1"/>
  </svg>
  <!-- Floating Battery Charge -->
  <svg class="e-icon i4" width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2">
    <rect x="3" y="7" width="16" height="10" rx="2"/>
    <line x1="21" y1="10" x2="21" y2="14"/>
    <path d="M11 9l-2 3h4l-2 3" fill="#a78bfa"/>
  </svg>
  <!-- Floating Lightning Bolt 2 -->
  <svg class="e-icon i5" width="32" height="32" viewBox="0 0 24 24" fill="#38bdf8">
    <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z"/>
  </svg>
</div>

<div class="e-wave-wrap" aria-hidden="true">
  <div class="e-wave-track">
    <svg viewBox="0 0 600 54" preserveAspectRatio="none" style="width:50%;height:100%">
      <path d="M0,27 Q75,2 150,27 T300,27 T450,27 T600,27" fill="none" stroke="#10b981" stroke-width="2"/>
      <path d="M0,34 Q75,12 150,34 T300,34 T450,34 T600,34" fill="none" stroke="#38bdf8" stroke-width="1.4" opacity="0.6"/>
    </svg>
    <svg viewBox="0 0 600 54" preserveAspectRatio="none" style="width:50%;height:100%">
      <path d="M0,27 Q75,2 150,27 T300,27 T450,27 T600,27" fill="none" stroke="#10b981" stroke-width="2"/>
      <path d="M0,34 Q75,12 150,34 T300,34 T450,34 T600,34" fill="none" stroke="#38bdf8" stroke-width="1.4" opacity="0.6"/>
    </svg>
  </div>
</div>
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
    st.markdown("### ⚡ Settings")
    profile_name = st.selectbox("Home / Building", list(PROFILES.keys()))
    preset = PROFILES[profile_name]

    data_source = st.radio("Data", ["Simulator", "Upload CSV"], horizontal=True)
    uploaded = None
    if data_source == "Upload CSV":
        uploaded = st.file_uploader("Upload CSV (`timestamp`, `total_kwh`)", type=["csv"])
        days, inject_spikes, seed, ac_savings = 14, 5, preset["seed"], 0
        use_custom_kw, custom_avg_kw, manual_spike_kw = False, None, 0.0
    else:
        days = st.slider("Days to show", min_value=3, max_value=30, value=14)
        use_custom_kw = st.toggle("Set my own power (kW)", value=False)
        custom_avg_kw = None
        if use_custom_kw:
            custom_avg_kw = st.number_input(
                "Average power (kW)",
                min_value=0.2,
                max_value=25.0,
                value=round(1.5 * preset["scale"], 2),
                step=0.1,
            )
        manual_spike_kw = st.number_input(
            "Add manual spike on latest hour (+kW)",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.5,
            help="Type a number above 0 (e.g. 3.5) to test a live spike right now.",
        )
        inject_spikes = st.slider("Random power spikes", min_value=0, max_value=12, value=5)
        seed = st.number_input("Seed", min_value=1, max_value=9999, value=preset["seed"], step=1)
        ac_savings = st.slider("Lower AC usage by (%)", min_value=0, max_value=40, value=0, step=5)

    st.divider()
    st.markdown("### 💳 Rate & Budget (Estimate)")
    tariff_mode = st.selectbox(
        "Electricity rate",
        ["Malaysia 2025–2027 Estimate (MYR)", "Time-of-Use (Peak / Off-Peak)", "Custom Flat Rate"],
    )
    rates_2025 = TariffRates2025()
    custom_rate = 0.45
    if tariff_mode == "Malaysia 2025–2027 Estimate (MYR)":
        with st.expander("Adjust 2025–2027 rate components"):
            e_std = st.number_input("Energy <=1500 kWh (RM/kWh)", value=0.2703, step=0.005, format="%.4f")
            cap_r = st.number_input("Capacity charge (RM/kWh)", value=0.0455, step=0.005, format="%.4f")
            net_r = st.number_input("Network charge (RM/kWh)", value=0.1285, step=0.005, format="%.4f")
            afa_r = st.number_input("AFA fuel adjustment (RM/kWh)", value=0.0000, step=0.005, format="%.4f")
            ret_m = st.number_input("Monthly retail charge (>600 kWh, RM)", value=10.00, step=1.0)
            rates_2025 = TariffRates2025(
                energy_standard=e_std,
                capacity_rate=cap_r,
                network_rate=net_r,
                afa_rate=afa_r,
                retail_monthly=ret_m,
            )
    elif tariff_mode == "Custom Flat Rate":
        custom_rate = st.number_input("Rate (RM / kWh)", min_value=0.05, max_value=2.00, value=0.45, step=0.01)

    monthly_budget = st.number_input(
        "Monthly budget (RM)", min_value=50.0, max_value=2000.0, value=preset["budget"], step=10.0
    )
    co2_factor = st.number_input(
        "Grid CO2 factor (kg / kWh)", min_value=0.1, max_value=1.5, value=DEFAULT_CO2_KG_PER_KWH, step=0.01, format="%.3f"
    )

    st.divider()
    st.markdown("### 🚨 Spike Alerts")
    z_threshold = st.slider(
        "Alert sensitivity",
        min_value=1.5,
        max_value=4.0,
        value=2.5,
        step=0.1,
        help="Lower number = catches smaller spikes; higher = only big spikes.",
    )
    aggregate_daily = st.toggle("Group chart by day", value=False)

# ---------- Load / Simulate Data ----------
csv_report = None
if data_source == "Upload CSV" and uploaded is not None:
    try:
        raw_df, csv_report = load_uploaded_csv(uploaded)
        data_mode_label = "Uploaded CSV Data"
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
        st.stop()
else:
    data_mode_label = "Simulated Data (No Physical Meter)"
    if data_source == "Upload CSV":
        st.info("Upload a CSV with `timestamp` and `total_kwh` columns — showing simulated data until a file is uploaded.")
    raw_df = simulate_consumption(
        days=days,
        seed=int(seed),
        inject_anomalies=inject_spikes,
        ac_reduction_pct=float(ac_savings),
    )
    app_cols = ["Air Conditioning", "Refrigerator", "Lighting", "Water Heater", "Home Office & IT", "total_kwh"]
    if use_custom_kw and custom_avg_kw is not None:
        current_avg = float(raw_df["total_kwh"].mean())
        scale = (custom_avg_kw / current_avg) if current_avg > 0 else 1.0
    else:
        scale = preset["scale"]
    if scale != 1.0:
        for col in app_cols:
            raw_df[col] = (raw_df[col] * scale).round(3)

    if manual_spike_kw > 0 and len(raw_df) > 0:
        last_idx = raw_df.index[-1]
        raw_df.loc[last_idx, "Air Conditioning"] = round(float(raw_df.loc[last_idx, "Air Conditioning"]) + manual_spike_kw, 3)
        raw_df.loc[last_idx, "total_kwh"] = round(float(raw_df.loc[last_idx, "total_kwh"]) + manual_spike_kw, 3)

analyzed_df = detect_anomalies(raw_df, window=24, z_threshold=z_threshold)
costs = estimate_costs(analyzed_df, tariff_mode=tariff_mode, rates_2025=rates_2025, custom_rate=custom_rate)
carbon = estimate_carbon_emissions(costs.total_kwh, costs.projected_30d_kwh, factor_kg_per_kwh=co2_factor)
anomalies_df = analyzed_df[analyzed_df["is_anomaly"]].copy()
night_load = phantom_overnight_load(analyzed_df)
breakdown = appliance_breakdown(analyzed_df)
appliance_table = appliance_summary_table(analyzed_df, avg_rate_rm=costs.avg_rate_per_kwh)
profile = hourly_profile(analyzed_df)
forecast_df = forecast_next_7_days(analyzed_df)
last_hour_kwh = float(analyzed_df["total_kwh"].iloc[-1])

# ---------- Animated Hero Header + Honest Source Badge & Accurate Units ----------
badge_color = "#38bdf8" if csv_report is None else "#a78bfa"
hero_html = (
    '<div class="hero-box"><div class="hero-grid">'
    '<div>'
    f'<div class="hero-badge" style="color:{badge_color};border-color:{badge_color}55;background:{badge_color}1a">'
    f'<span class="hero-dot" style="background:{badge_color}"></span> {data_mode_label} · {profile_name}</div>'
    '<h1 class="hero-title">Smart Energy Monitor</h1>'
    '<p class="hero-sub">By <b>Muhammad Abdullahi Bukar</b> — Track hourly energy (kWh), average power (kW), '
    'estimated Malaysia 2025–2027 bills, CO₂ impact, and unusual power spikes.</p>'
    '</div>'
    '<div>'
    '<svg viewBox="0 0 360 118" width="100%" role="img" aria-label="Simulated power flow">'
    '<line x1="42" y1="42" x2="42" y2="96" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>'
    '<g class="e-spin" stroke="#38bdf8" stroke-width="3" stroke-linecap="round">'
    '<line x1="42" y1="42" x2="42" y2="16"/>'
    '<line x1="42" y1="42" x2="64" y2="55"/>'
    '<line x1="42" y1="42" x2="20" y2="55"/>'
    '</g>'
    '<circle cx="42" cy="42" r="4" fill="#e0f2fe"/>'
    '<text x="42" y="110" text-anchor="middle" fill="#94a3b8" font-size="10">Grid / Sim</text>'
    '<path d="M58 68 H148" stroke="rgba(56,189,248,0.22)" stroke-width="5" stroke-linecap="round"/>'
    '<path class="flow-line" d="M58 68 H148" stroke="#38bdf8" stroke-width="3" stroke-linecap="round"/>'
    '<rect x="140" y="38" width="80" height="58" rx="12" fill="rgba(15,23,42,0.9)" stroke="#34d399" stroke-width="2"/>'
    f'<text x="180" y="61" text-anchor="middle" fill="#6ee7b7" font-size="11" font-weight="700">{last_hour_kwh:.2f} kWh</text>'
    '<text x="180" y="75" text-anchor="middle" fill="#94a3b8" font-size="8.5">LAST HOUR</text>'
    f'<text x="180" y="88" text-anchor="middle" fill="#38bdf8" font-size="8.5">Avg {costs.avg_power_kw:.2f} kW</text>'
    '<path d="M220 68 H292" stroke="rgba(16,185,129,0.22)" stroke-width="5" stroke-linecap="round"/>'
    '<path class="flow-line-amber" d="M220 68 H292" stroke="#34d399" stroke-width="3" stroke-linecap="round"/>'
    '<path d="M292 56 L320 34 L348 56 V94 H292 Z" fill="rgba(30,41,59,0.95)" stroke="#38bdf8" stroke-width="2" stroke-linejoin="round"/>'
    '<rect x="303" y="63" width="10" height="10" rx="2" fill="#fbbf24"/>'
    '<rect x="327" y="63" width="10" height="10" rx="2" fill="#34d399"/>'
    '<rect x="315" y="79" width="10" height="15" rx="1" fill="#38bdf8"/>'
    '<text x="320" y="110" text-anchor="middle" fill="#94a3b8" font-size="10">Home</text>'
    '</svg>'
    '</div>'
    '</div></div>'
)
st.markdown(hero_html, unsafe_allow_html=True)

if csv_report and csv_report.warnings:
    with st.expander(f"CSV Validation Notices ({len(csv_report.warnings)})", expanded=True):
        for w in csv_report.warnings:
            st.warning(w)

# ---------- Glass KPI Cards ----------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Energy Used", f"{costs.total_kwh:,.2f} kWh", f"Last hour: {last_hour_kwh:.2f} kWh")
c2.metric("Average Power", f"{costs.avg_power_kw:.2f} kW", f"Over {costs.span_hours:.0f} hrs")
budget_delta = costs.projected_30d_cost - monthly_budget
c3.metric(
    "Est. Monthly Bill",
    f"{costs.currency} {costs.projected_30d_cost:,.2f}",
    f"{budget_delta:+.2f} {costs.currency} vs budget",
    delta_color="inverse",
)
c4.metric("Est. Monthly CO₂", f"{carbon.projected_30d_co2_kg:,.1f} kg", f"~{carbon.trees_needed_monthly:.0f} trees/mo", delta_color="off")
c5.metric("Unusual Spikes", f"{len(anomalies_df)}", f"Night avg: {night_load:.2f} kWh/h", delta_color="off")

budget_ratio = min(1.0, costs.projected_30d_cost / max(1.0, monthly_budget))
if costs.projected_30d_cost > monthly_budget:
    st.warning(
        f"Your estimated 30-day bill (**{costs.currency} {costs.projected_30d_cost:,.2f}**) is over your "
        f"**{costs.currency} {monthly_budget:,.2f}** budget. Try lowering AC usage in the left sidebar."
    )
st.progress(budget_ratio, text=f"Monthly budget used: {int((costs.projected_30d_cost / max(1.0, monthly_budget)) * 100)}%")

# ---------- Tabs ----------
tab_overview, tab_apps, tab_forecast, tab_alerts, tab_reports = st.tabs(
    [
        "📈 Charts",
        "🔌 Appliances",
        "🔮 Forecast & CO₂",
        f"🚨 Spikes & MQTT ({len(anomalies_df)})",
        "📄 Reports & Export",
    ]
)

with tab_overview:
    st.subheader("Energy Usage Over Time (kWh)")
    components.html(render_timeseries_chart(analyzed_df, aggregate_daily=aggregate_daily), height=375)

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Share by Appliance (kWh)")
        components.html(render_appliance_doughnut(breakdown), height=330)
    with col_right:
        st.subheader("Busiest Hours of the Day")
        components.html(render_hourly_bar_chart(profile), height=330)

with tab_apps:
    st.subheader("Per-Appliance Usage & Estimated Cost")
    st.dataframe(appliance_table, use_container_width=True, hide_index=True)

    selected_app = st.selectbox("Inspect individual appliance trend", APPLIANCES)
    if selected_app in analyzed_df.columns:
        app_series = analyzed_df[["timestamp", selected_app]].tail(168).set_index("timestamp")
        st.line_chart(app_series, height=260)

with tab_forecast:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.subheader("Next 7-Day Energy Forecast (kWh/day)")
        st.caption("Estimated from recent daily totals, trend, and weekend pattern.")
        if not forecast_df.empty:
            st.bar_chart(forecast_df.set_index("date")["predicted_kwh"], height=250)
            st.dataframe(
                forecast_df.rename(columns={"date": "Date", "predicted_kwh": "Predicted (kWh)"}),
                use_container_width=True,
                hide_index=True,
            )
    with col_f2:
        st.subheader("Estimated Monthly Bill Breakdown")
        st.caption(f"Tariff: **{tariff_mode}** *(estimate only — adjust components in sidebar)*")
        if costs.breakdown:
            bd_rows = [{"Component": k, "Est. Amount (RM)": v} for k, v in costs.breakdown.items()]
            st.dataframe(bd_rows, use_container_width=True, hide_index=True)

        st.subheader("Carbon Footprint Estimate")
        st.info(
            f"**Period:** {carbon.period_co2_kg:,.2f} kg CO₂e  \n"
            f"**Projected 30-day:** {carbon.projected_30d_co2_kg:,.2f} kg CO₂e "
            f"(using `{carbon.factor_kg_per_kwh:.3f} kg CO₂/kWh` grid factor — equivalent to ~{carbon.trees_needed_monthly:.0f} trees absorbing CO₂ for a month)."
        )

with tab_alerts:
    st.subheader("Unusual Power Spikes Found")
    st.caption(
        f"Baseline uses **previous 24 hours only** (`.shift(1)`) so a spike never hides itself "
        f"(sensitivity: **{z_threshold:.1f}**)."
    )
    if anomalies_df.empty:
        st.success("No unusual power spikes found at this sensitivity level.")
    else:
        display_cols = ["timestamp", "total_kwh", "baseline_kwh", "z_score", "severity", "reason"]
        pretty = anomalies_df[display_cols].sort_values("timestamp", ascending=False).rename(
            columns={
                "timestamp": "Time",
                "total_kwh": "Actual (kWh)",
                "baseline_kwh": "Normal (kWh)",
                "z_score": "Spike Score",
                "severity": "Level",
                "reason": "Explanation",
            }
        )
        st.dataframe(pretty, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Simulated MQTT Telemetry Stream")
    st.caption("Shows how an IoT smart meter would publish these readings and alerts over MQTT topics (simulated in software).")
    slug = profile_name.lower().split("(")[0].strip().replace(" ", "-").replace("/", "")
    mqtt_msgs = build_mqtt_messages(analyzed_df, profile_slug=slug, limit=6)
    st.dataframe(mqtt_msgs, use_container_width=True, hide_index=True)

with tab_reports:
    st.subheader("Export Reports")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        csv_bytes = analyzed_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Data Report (CSV)",
            data=csv_bytes,
            file_name="smart-energy-report.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_dl2:
        pdf_bytes = build_pdf_report(
            profile_name=profile_name,
            data_mode=data_mode_label,
            tariff_mode=tariff_mode,
            costs=costs,
            carbon=carbon,
            appliance_df=appliance_table,
            anomalies_df=anomalies_df,
        )
        st.download_button(
            label="📄 Download Summary Report (PDF)",
            data=pdf_bytes,
            file_name="smart-energy-summary.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.subheader("Hourly Power Readings")
    st.dataframe(analyzed_df.tail(200), use_container_width=True, hide_index=True)
