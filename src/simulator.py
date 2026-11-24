"""Hourly electricity usage simulator and validated CSV loader."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

APPLIANCES = [
    "Air Conditioning",
    "Refrigerator",
    "Lighting",
    "Water Heater",
    "Home Office & IT",
]


@dataclass(frozen=True)
class CsvValidationReport:
    rows_loaded: int
    invalid_timestamps_dropped: int
    duplicate_timestamps_merged: int
    missing_values_dropped: int
    negative_values_rejected: int
    irregular_intervals_found: int
    warnings: list[str]


def simulate_consumption(
    days: int = 14,
    seed: int = 42,
    inject_anomalies: int = 4,
    ac_reduction_pct: float = 0.0,
) -> pd.DataFrame:
    """
    Generate hourly electricity usage (kWh) per appliance with day/night
    and weekend patterns, plus optional random power spikes.
    """
    rng = np.random.default_rng(seed)
    end = datetime.now().replace(minute=0, second=0, microsecond=0)
    hours = max(24, int(days) * 24)
    timestamps = [end - timedelta(hours=hours - 1 - i) for i in range(hours)]

    ac_scale = max(0.2, 1.0 - (ac_reduction_pct / 100.0))
    rows: list[dict[str, object]] = []

    for ts in timestamps:
        h = ts.hour
        is_weekend = ts.weekday() >= 5

        # Day/night usage profiles (kWh per hour)
        ac_base = (1.35 if 12 <= h <= 17 else 0.95 if 18 <= h <= 23 else 0.35) * (1.12 if is_weekend else 1.0)
        ac_kwh = max(0.05, rng.normal(ac_base, 0.14)) * ac_scale

        fridge_kwh = max(0.08, rng.normal(0.16, 0.025))

        light_base = 0.42 if (19 <= h <= 23) else (0.18 if 6 <= h <= 8 else 0.05)
        light_kwh = max(0.01, rng.normal(light_base, 0.03))

        heater_base = 0.85 if h in (7, 8, 20, 21) else 0.04
        heater_kwh = max(0.01, rng.normal(heater_base, 0.06))

        office_base = 0.32 if (9 <= h <= 18 and not is_weekend) else (0.22 if 19 <= h <= 22 else 0.07)
        office_kwh = max(0.02, rng.normal(office_base, 0.04))

        total_kwh = ac_kwh + fridge_kwh + light_kwh + heater_kwh + office_kwh
        rows.append(
            {
                "timestamp": ts,
                "Air Conditioning": round(ac_kwh, 3),
                "Refrigerator": round(fridge_kwh, 3),
                "Lighting": round(light_kwh, 3),
                "Water Heater": round(heater_kwh, 3),
                "Home Office & IT": round(office_kwh, 3),
                "total_kwh": round(total_kwh, 3),
                "injected_fault": False,
            }
        )

    df = pd.DataFrame(rows)

    if inject_anomalies > 0 and len(df) > 30:
        candidate_idx = rng.choice(
            np.arange(24, len(df) - 1),
            size=min(inject_anomalies, len(df) - 25),
            replace=False,
        )
        for idx in candidate_idx:
            spike_appliance = str(rng.choice(["Air Conditioning", "Water Heater", "Home Office & IT"]))
            extra = float(rng.uniform(2.2, 4.0))
            df.loc[idx, spike_appliance] = round(float(df.loc[idx, spike_appliance]) + extra, 3)
            df.loc[idx, "total_kwh"] = round(float(df.loc[idx, "total_kwh"]) + extra, 3)
            df.loc[idx, "injected_fault"] = True

    return df


def load_uploaded_csv(file_obj: object) -> tuple[pd.DataFrame, CsvValidationReport]:
    """
    Parse and strictly validate a user-uploaded meter CSV (`timestamp`, `total_kwh`).
    Checks invalid timestamps, duplicates, missing/non-numeric values, negative readings,
    and irregular time intervals.
    """
    df = pd.read_csv(file_obj)
    cols = {c.lower().strip(): c for c in df.columns}
    if "timestamp" not in cols or "total_kwh" not in cols:
        raise ValueError("CSV must contain 'timestamp' and 'total_kwh' columns.")

    df = df.rename(columns={cols["timestamp"]: "timestamp", cols["total_kwh"]: "total_kwh"})
    warnings: list[str] = []

    # 1. Invalid timestamps
    parsed_ts = pd.to_datetime(df["timestamp"], errors="coerce")
    invalid_ts = int(parsed_ts.isna().sum())
    if invalid_ts > 0:
        warnings.append(f"Dropped {invalid_ts} row(s) with invalid timestamps.")
    df = df.loc[parsed_ts.notna()].copy()
    df["timestamp"] = parsed_ts[parsed_ts.notna()]

    # 2. Missing or non-numeric consumption values
    parsed_kwh = pd.to_numeric(df["total_kwh"], errors="coerce")
    missing_vals = int(parsed_kwh.isna().sum())
    if missing_vals > 0:
        warnings.append(f"Dropped {missing_vals} row(s) with missing or non-numeric kWh values.")
    df = df.loc[parsed_kwh.notna()].copy()
    df["total_kwh"] = parsed_kwh[parsed_kwh.notna()]

    # 3. Negative consumption values
    neg_mask = df["total_kwh"] < 0
    neg_count = int(neg_mask.sum())
    if neg_count > 0:
        warnings.append(f"Removed {neg_count} row(s) with negative kWh values.")
    df = df.loc[~neg_mask].copy()

    if df.empty:
        raise ValueError("No valid rows remained after CSV validation.")

    # 4. Duplicate timestamps (keep latest reading for each timestamp)
    df = df.sort_values("timestamp")
    dup_count = int(df.duplicated(subset=["timestamp"]).sum())
    if dup_count > 0:
        warnings.append(f"Merged {dup_count} duplicate timestamp(s) (kept latest value).")
        df = df.drop_duplicates(subset=["timestamp"], keep="last")
    df = df.reset_index(drop=True)

    # 5. Irregular time intervals
    irregular_count = 0
    if len(df) >= 3:
        diffs_min = df["timestamp"].diff().dropna().dt.total_seconds() / 60.0
        median_min = float(diffs_min.median())
        if median_min > 0:
            irregular_count = int(((diffs_min - median_min).abs() > max(2.0, median_min * 0.1)).sum())
            if irregular_count > 0:
                warnings.append(
                    f"Detected {irregular_count} irregular time gap(s) (typical interval: {median_min:.0f} min). "
                    "Monthly projection uses actual elapsed hours."
                )

    # Fill missing appliance columns proportionally
    shares = {
        "Air Conditioning": 0.44,
        "Refrigerator": 0.12,
        "Lighting": 0.14,
        "Water Heater": 0.16,
        "Home Office & IT": 0.14,
    }
    for app_name, share in shares.items():
        if app_name not in df.columns:
            df[app_name] = (df["total_kwh"] * share).round(3)

    if "injected_fault" not in df.columns:
        df["injected_fault"] = False

    report = CsvValidationReport(
        rows_loaded=len(df),
        invalid_timestamps_dropped=invalid_ts,
        duplicate_timestamps_merged=dup_count,
        missing_values_dropped=missing_vals,
        negative_values_rejected=neg_count,
        irregular_intervals_found=irregular_count,
        warnings=warnings,
    )
    return df, report
