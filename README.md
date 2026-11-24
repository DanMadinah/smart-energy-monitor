# Smart Energy Monitor

Live app: [smart-energy-monitor-evhjv9owzhp7ad8vsfbnqp.streamlit.app](https://smart-energy-monitor-evhjv9owzhp7ad8vsfbnqp.streamlit.app/)

A **software-simulated IoT energy monitoring prototype** built with Python, Streamlit, Pandas, and Chart.js. It simulates household electricity usage (or validates uploaded CSV meter logs), estimates monthly bills, forecasts 7-day demand, estimates CO₂ emissions, and flags unusual power spikes — with no physical hardware required.

## What it does

- **Simulated meter & validated CSV upload**: Generates hourly `kWh` usage across 5 appliances (Air Conditioning, Refrigerator, Lighting, Water Heater, Home Office & IT) with custom average kW and manual spike controls. CSV uploads are checked for invalid timestamps, duplicates, missing/negative values, and irregular gaps.
- **Malaysia 2025–2027 bill estimator**: Configurable estimate covering Energy, Capacity, Network, AFA fuel adjustment, and Monthly Retail Charge (waived at <= 600 kWh), alongside Peak/Off-Peak and Custom Flat Rate options.
- **Unbiased spike detection**: Uses a shifted 24-hour rolling baseline (`.shift(1)`) so abnormal spikes never hide themselves, with plain-English explanations pointing to the main appliance.
- **Per-appliance trends, 7-day forecast & CO₂ estimate**: Inspect individual appliance costs and history, view a 7-day usage forecast, and estimate monthly CO₂ emissions (`0.585 kg CO₂/kWh` default Peninsular Malaysia factor).
- **Simulated MQTT telemetry & reports**: Displays MQTT-style IoT topic/JSON payloads (`home/<profile>/meter/reading`, `home/<profile>/alerts/spike`) and exports both **CSV** and **PDF** summary reports.

## Tech stack

- Python 3.11, Streamlit, Pandas, NumPy, Chart.js 4, fpdf2
- Pytest + GitHub Actions CI

## Files

```text
smart-energy-monitor/
├── .github/workflows/ci.yml    # Syntax check and Pytest CI
├── .streamlit/config.toml      # Dark theme settings
├── docs/ARCHITECTURE.md        # Data flow and design notes
├── src/
│   ├── simulator.py            # Hourly usage simulator and validated CSV loader
│   ├── tariffs.py              # Malaysia 2025–2027, TOU, and flat rate estimator
│   ├── analytics.py            # Shifted Z-score detector, CO2, and 7-day forecast
│   ├── mqtt_sim.py             # Simulated MQTT IoT topic/payload stream
│   ├── report.py               # Downloadable PDF summary report builder
│   └── charts.py               # Chart.js 4 HTML builders
├── tests/
│   └── test_energy_engine.py   # Pytest suite covering tariffs, CSV, spikes, MQTT & PDF
├── app.py                      # Main Streamlit dashboard
├── requirements.txt
└── LICENSE
```

## Running or deploying

- **Streamlit Cloud**: Connect this repo on [share.streamlit.io](https://share.streamlit.io) with `app.py` as the main file.
- **Local**:
  ```bash
  pip install -r requirements.txt
  streamlit run app.py
  ```
- **Tests**:
  ```bash
  PYTHONPATH=. pytest -v
  ```

## Author

Muhammad Abdullahi Bukar

## License

MIT — see [LICENSE](LICENSE).
