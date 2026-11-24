"""Interactive Chart.js 4.x animated components with gradients and glass tooltips."""

from __future__ import annotations

import json
import pandas as pd

COMMON_CSS = """
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: transparent;
    font-family: Inter, system-ui, -apple-system, sans-serif;
    overflow: hidden;
  }
  .card {
    background: rgba(15, 23, 42, 0.58);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 18px;
    padding: 14px 16px;
    backdrop-filter: blur(12px);
    box-shadow: 0 12px 32px rgba(2, 6, 23, 0.35);
    animation: fadeUp 0.65s cubic-bezier(0.22, 1, 0.36, 1) both;
  }
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
  }
"""


def render_timeseries_chart(df: pd.DataFrame, aggregate_daily: bool = False) -> str:
    """Animated gradient line chart of energy usage over time with anomaly markers."""
    tmp = df.copy()
    tmp["timestamp"] = pd.to_datetime(tmp["timestamp"])

    if aggregate_daily:
        daily = (
            tmp.set_index("timestamp")
            .resample("D")
            .agg(total_kwh=("total_kwh", "sum"), baseline_kwh=("baseline_kwh", "sum"), is_anomaly=("is_anomaly", "any"))
            .reset_index()
        )
        labels = [ts.strftime("%b %d") for ts in daily["timestamp"]]
        values = [round(float(v), 2) for v in daily["total_kwh"]]
        baseline = [round(float(v), 2) for v in daily["baseline_kwh"]]
        anomaly_pts = [round(float(r.total_kwh), 2) if r.is_anomaly else None for r in daily.itertuples()]
        unit_label = "Daily Energy (kWh)"
    else:
        tail = tmp.tail(168)
        labels = [ts.strftime("%b %d %H:%M") for ts in tail["timestamp"]]
        values = [round(float(v), 3) for v in tail["total_kwh"]]
        baseline = [round(float(v), 3) for v in tail["baseline_kwh"]]
        anomaly_pts = [round(float(r.total_kwh), 3) if r.is_anomaly else None for r in tail.itertuples()]
        unit_label = "Hourly Consumption (kWh)"

    return f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"></script>
  <style>{COMMON_CSS} .wrap {{ position: relative; height: 330px; width: 100%; }}</style>
</head>
<body>
  <div class="card"><div class="wrap"><canvas id="tsChart"></canvas></div></div>
  <script>
    const ctx = document.getElementById('tsChart').getContext('2d');
    const grad = ctx.createLinearGradient(0, 0, 0, 320);
    grad.addColorStop(0, 'rgba(16, 185, 129, 0.42)');
    grad.addColorStop(0.65, 'rgba(6, 182, 212, 0.12)');
    grad.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: {json.dumps(labels)},
        datasets: [
          {{
            label: {json.dumps(unit_label)},
            data: {json.dumps(values)},
            borderColor: '#34d399',
            backgroundColor: grad,
            borderWidth: 2.5,
            fill: true,
            tension: 0.34,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: '#34d399',
            pointHoverBorderColor: '#ffffff',
            pointHoverBorderWidth: 2
          }},
          {{
            label: '24h Rolling Baseline',
            data: {json.dumps(baseline)},
            borderColor: 'rgba(148, 163, 184, 0.7)',
            borderDash: [6, 5],
            borderWidth: 1.5,
            fill: false,
            pointRadius: 0
          }},
          {{
            label: 'Detected Anomaly',
            data: {json.dumps(anomaly_pts)},
            borderColor: '#fb7185',
            backgroundColor: '#f43f5e',
            borderWidth: 2,
            showLine: false,
            pointRadius: 6.5,
            pointHoverRadius: 9
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        animation: {{ duration: 1100, easing: 'easeOutQuart' }},
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ labels: {{ color: '#e2e8f0', boxWidth: 12, usePointStyle: true, padding: 16 }} }},
          tooltip: {{
            backgroundColor: 'rgba(15, 23, 42, 0.92)',
            borderColor: 'rgba(52, 211, 153, 0.45)',
            borderWidth: 1,
            padding: 12,
            cornerRadius: 10,
            titleColor: '#f8fafc',
            bodyColor: '#cbd5e1'
          }}
        }},
        scales: {{
          x: {{ ticks: {{ color: '#94a3b8', maxTicksLimit: 10 }}, grid: {{ color: 'rgba(148,163,184,0.06)' }} }},
          y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""


def render_appliance_doughnut(breakdown: dict[str, float]) -> str:
    """Animated Chart.js doughnut chart with hover pop-out."""
    labels = list(breakdown.keys())
    values = list(breakdown.values())
    colors = ["#10b981", "#38bdf8", "#f59e0b", "#f43f5e", "#a78bfa"]

    return f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"></script>
  <style>{COMMON_CSS} .wrap {{ position: relative; height: 285px; width: 100%; }}</style>
</head>
<body>
  <div class="card"><div class="wrap"><canvas id="donutChart"></canvas></div></div>
  <script>
    new Chart(document.getElementById('donutChart'), {{
      type: 'doughnut',
      data: {{
        labels: {json.dumps(labels)},
        datasets: [{{
          data: {json.dumps(values)},
          backgroundColor: {json.dumps(colors[:len(labels)])},
          borderColor: 'rgba(15, 23, 42, 0.9)',
          borderWidth: 3,
          hoverOffset: 10
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        cutout: '64%',
        animation: {{ animateRotate: true, animateScale: true, duration: 1050, easing: 'easeOutBack' }},
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ color: '#e2e8f0', padding: 14, usePointStyle: true }} }},
          tooltip: {{
            backgroundColor: 'rgba(15, 23, 42, 0.92)',
            borderColor: 'rgba(56, 189, 248, 0.4)',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 10
          }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""


def render_hourly_bar_chart(profile_df: pd.DataFrame) -> str:
    """Animated Chart.js 24-hour bar chart highlighting Peak vs Off-Peak hours."""
    labels = [f"{int(h):02d}:00" for h in profile_df["hour"]]
    values = [round(float(v), 3) for v in profile_df["total_kwh"]]
    colors = [
        "rgba(245, 158, 11, 0.88)" if 14 <= int(h) <= 22 else "rgba(56, 189, 248, 0.8)"
        for h in profile_df["hour"]
    ]

    return f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"></script>
  <style>{COMMON_CSS} .wrap {{ position: relative; height: 285px; width: 100%; }}</style>
</head>
<body>
  <div class="card"><div class="wrap"><canvas id="barChart"></canvas></div></div>
  <script>
    new Chart(document.getElementById('barChart'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(labels)},
        datasets: [{{
          label: 'Avg kWh (Amber = Peak 14:00–22:00)',
          data: {json.dumps(values)},
          backgroundColor: {json.dumps(colors)},
          borderRadius: 7,
          borderSkipped: false
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        animation: {{ duration: 950, easing: 'easeOutQuart' }},
        plugins: {{
          legend: {{ labels: {{ color: '#e2e8f0', usePointStyle: true }} }},
          tooltip: {{
            backgroundColor: 'rgba(15, 23, 42, 0.92)',
            borderColor: 'rgba(245, 158, 11, 0.45)',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 10
          }}
        }},
        scales: {{
          x: {{ ticks: {{ color: '#94a3b8', maxTicksLimit: 12 }}, grid: {{ display: false }} }},
          y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.1)' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""
