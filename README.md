# Smart Campus Digital Twin

AI digital twin of a simulated smart campus that monitors, forecasts and optimizes energy use.

> Status: Week 1 of 12 (foundation). Results will be added only after experiments are run.
> All results are simulation-based. The system recommends actions; it does not control real equipment.

## Goal
Monitor, forecast, detect anomalies in, and recommend savings for the energy use of a simulated campus of 5-10 buildings.

## Planned stack
Python, MQTT (Mosquitto), FastAPI, PostgreSQL + TimescaleDB, LightGBM, scikit-learn, Streamlit, Docker Compose.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Repository layout
See the folder names: `config/`, `data/`, `simulator/`, `broker/`, `database/`, `api/`, `twin/`, `features/`, `models/`, `optimization/`, `carbon/`, `dashboard/`, `reports/`, `notebooks/`, `scripts/`, `docker/`, `tests/`, `docs/`.

## Results
_To be added._

## Limitations
_To be added in `docs/limitations.md`._
