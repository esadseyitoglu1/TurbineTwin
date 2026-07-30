# Wind Turbine Digital Twin (TurbineTwin)

A prototype digital twin for wind turbine anomaly detection, built on real SCADA
data. Compares actual power output against the manufacturer's theoretical power
curve to flag deviations from design behavior.

## Setup

```powershell
py -3.14 -m venv .venv --system-site-packages
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Dataset

See [data/raw/README.md](data/raw/README.md) for download instructions.

## Status

Phase 1 (data + model) in progress.
