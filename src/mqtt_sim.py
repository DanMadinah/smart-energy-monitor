"""Simulated MQTT IoT telemetry pipeline (demonstrates broker topic design without hardware)."""

from __future__ import annotations

import json
import pandas as pd


def build_mqtt_messages(df: pd.DataFrame, profile_slug: str = "family-house", limit: int = 8) -> list[dict[str, object]]:
    """
    Generate MQTT-style publish packets (topic, qos, retain, JSON payload)
    from the latest meter readings and detected spikes.
    """
    if df.empty:
        return []

    messages: list[dict[str, object]] = []
    tail = df.tail(limit).iloc[::-1]

    for row in tail.itertuples():
        ts_iso = pd.to_datetime(row.timestamp).isoformat()
        reading_payload = {
            "device_id": f"sim-meter-{profile_slug}",
            "timestamp": ts_iso,
            "energy_kwh": round(float(row.total_kwh), 3),
            "avg_power_kw": round(float(row.total_kwh), 3),
            "baseline_kwh": round(float(row.baseline_kwh), 3),
            "status": str(row.severity),
        }
        messages.append(
            {
                "Topic": f"home/{profile_slug}/meter/reading",
                "QoS": 1,
                "Retain": True,
                "Payload": json.dumps(reading_payload),
            }
        )

        if bool(row.is_anomaly):
            alert_payload = {
                "timestamp": ts_iso,
                "severity": str(row.severity),
                "z_score": float(row.z_score),
                "top_appliance": str(row.top_appliance),
                "reason": str(row.reason),
            }
            messages.append(
                {
                    "Topic": f"home/{profile_slug}/alerts/spike",
                    "QoS": 2,
                    "Retain": False,
                    "Payload": json.dumps(alert_payload),
                }
            )

    return messages
