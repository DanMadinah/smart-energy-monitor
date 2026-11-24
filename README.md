# Smart Energy Monitor

Live app: [smart-energy-monitor-evhjv9owzhp7ad8vsfbnqp.streamlit.app](https://smart-energy-monitor-evhjv9owzhp7ad8vsfbnqp.streamlit.app/)

A software-only web app for tracking household electricity usage, estimating monthly bills, and spotting unusual power spikes. Built with Python, Streamlit, Pandas, and Chart.js.

## What it does

- **Usage simulator & CSV upload**: Generates hourly kWh readings for 5 common appliances (Air Conditioning, Refrigerator, Lighting, Water Heater, Home Office & IT) with day/night and weekend patterns. You can also upload your own CSV file (`timestamp`, `total_kwh`).
- **Interactive charts**: Uses Chart.js for the power-over-time line chart (with red markers on spikes), appliance share doughnut chart, and busiest-hours bar chart.
- **Bill & savings estimate**: Calculates period cost and projected 30-day bill using Malaysia TNB tiered rates (MYR), Peak/Off-Peak rates, or a custom flat rate. Includes a monthly budget bar and a slider to test lowering AC usage.
- **Spike detection**: Compares each hour against a 24-hour rolling average using a Z-score to flag sudden jumps, highlights the main appliance behind each spike, and lets you download the full table as CSV.

## Tech stack

- Python 3.11
- Streamlit
- Pandas & NumPy
- Chart.js 4
- Pytest + GitHub Actions

## Files

```text
smart-energy-monitor/
├── .github/workflows/ci.yml    # Runs syntax check and pytest on push
├── .streamlit/config.toml      # Dark theme settings
├── src/
│   ├── simulator.py            # Hourly usage generator and CSV loader
│   ├── tariffs.py              # TNB tiered, peak/off-peak, and flat rate math
│   ├── analytics.py            # Rolling average spike detection and summaries
│   └── charts.py               # Chart.js HTML builders
├── tests/
│   └── test_energy_engine.py   # Unit tests for simulator, tariffs, and spike detection
├── app.py                      # Main Streamlit app
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
  pytest -v
  ```

## Author

Muhammad Abdullahi Bukar

## License

MIT — see [LICENSE](LICENSE).
