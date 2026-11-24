"""Interactive Chart.js 4.x HTML components rendered inside Streamlit."""

from __future__ import annotations

import json
import pandas as pd


def render_timeseries_chart(df: pd.DataFrame, aggregate_daily: bool = False) -> str:
    """Line chart of energy usage over time with baseline and red anomaly markers."""
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
        # Cap to last 168 hours (7 days) for crisp interactive tooltips
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
  <style>
    body {{ margin: 0; background: transparent; font-family: system-ui, sans-serif; }}
    .wrap {{ position: relative; height: 340px; width: 100%; }}
  </style>
</head>
<body>
  <div class="wrap"><canvas id="tsChart"></canvas></div>
  <script>
    new Chart(document.getElementById('tsChart'), {{
      type: 'line',
      data: {{
        labels: {json.dumps(labels)},
        datasets: [
          {{
            label: {json.dumps(unit_label)},
            data: {json.dumps(values)},
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.14)',
            borderWidth: 2,
            fill: true,
            tension: 0.28,
            pointRadius: 0,
            pointHoverRadius: 5
          }},
          {{
            label: 'Rolling Baseline',
            data: {json.dumps(baseline)},
            borderColor: '#64748b',
            borderDash: [5, 5],
            borderWidth: 1.5,
            fill: false,
            pointRadius: 0
          }},
          {{
            label: 'Detected Anomaly',
            data: {json.dumps(anomaly_pts)},
            borderColor: '#ef4444',
            backgroundColor: '#ef4444',
            showLine: false,
            pointRadius: 6,
            pointHoverRadius: 8
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ labels: {{ color: '#cbd5e1', boxWidth: 12 }} }}
        }},
        scales: {{
          x: {{ ticks: {{ color: '#94a3b8', maxTicksLimit: 10 }}, grid: {{ color: 'rgba(148,163,184,0.08)' }} }},
          y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.12)' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""


def render_appliance_doughnut(breakdown: dict[str, float]) -> str:
    """Interactive Chart.js doughnut chart showing kWh share by appliance."""
    labels = list(breakdown.keys())
    values = list(breakdown.values())
    colors = ["#10b981", "#38bdf8", "#f59e0b", "#f43f5e", "#a78bfa"]

    return f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"></script>
  <style>
    body {{ margin: 0; background: transparent; font-family: system-ui, sans-serif; }}
    .wrap {{ position: relative; height: 290px; width: 100%; }}
  </style>
</head>
<body>
  <div class="wrap"><canvas id="donutChart"></canvas></div>
  <script>
    new Chart(document.getElementById('donutChart'), {{
      type: 'doughnut',
      data: {{
        labels: {json.dumps(labels)},
        datasets: [{{
          data: {json.dumps(values)},
          backgroundColor: {json.dumps(colors[:len(labels)])},
          borderColor: '#0b1120',
          borderWidth: 2
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ color: '#cbd5e1', padding: 12 }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""


def render_hourly_bar_chart(profile_df: pd.DataFrame) -> str:
    """Interactive Chart.js bar chart highlighting Peak (14:00–22:00) vs Off-Peak hours."""
    labels = [f"{int(h):02d}:00" for h in profile_df["hour"]]
    values = [round(float(v), 3) for v in profile_df["total_kwh"]]
    colors = ["#f59e0b" if 14 <= int(h) <= 22 else "#38bdf8" for h in profile_df["hour"]]

    return f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"></script>
  <style>
    body {{ margin: 0; background: transparent; font-family: system-ui, sans-serif; }}
    .wrap {{ position: relative; height: 290px; width: 100%; }}
  </style>
</head>
<body>
  <div class="wrap"><canvas id="barChart"></canvas></div>
  <script>
    new Chart(document.getElementById('barChart'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(labels)},
        datasets: [{{
          label: 'Avg kWh (Amber = Peak 14:00–22:00)',
          data: {json.dumps(values)},
          backgroundColor: {json.dumps(colors)},
          borderRadius: 5
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ labels: {{ color: '#cbd5e1' }} }}
        }},
        scales: {{
          x: {{ ticks: {{ color: '#94a3b8', maxTicksLimit: 12 }}, grid: {{ display: false }} }},
          y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(148,163,184,0.12)' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""
