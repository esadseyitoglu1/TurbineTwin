from pathlib import Path

# Project root: three levels up from this file (src/turbinetwin/config.py -> TurbineTwin/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "T1.csv"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"

# Synthetic maintenance records (Phase 4) -- see NOTLAR.md Step 4.1 for
# how the 3 logged / 2 unlogged anomaly clusters were chosen.
MAINTENANCE_LOG_PATH = PROCESSED_DATA_DIR / "maintenance_log.json"

# Manufacturer cut-in/cut-out wind speeds (m/s). Outside this range the
# turbine is expected to produce ~0 power by design, not by fault.
CUT_IN = 3.0
CUT_OUT = 25.0

# Seconds of real time between two consecutive stream emissions at speed=1x.
SIMULATED_INTERVAL_SECONDS = 1.0
DEFAULT_SPEED = 1

# Row offsets for the dashboard's "jump to a known anomaly" demo buttons
# (see /api/stream's `start` param). Hardcoded to this specific dataset --
# recompute if T1.csv is ever replaced. Chosen so each jump lands ~15 rows
# (~2.5h of simulated time) before the flagged point, giving a short lead-in
# of normal operation on the chart instead of opening straight on the spike.
#   - unexplained: 2018-01-11 09:20:00 (row 1475) -- first flagged anomaly
#     in the dataset, no overlapping maintenance record.
#   - maintenance-match: 2018-01-16 05:00:00 (row 2168) -- covered by
#     MNT-2018-0116 (rotor bearing replacement), see maintenance_log.json.
DEMO_ANOMALY_START_UNEXPLAINED = 1460
DEMO_ANOMALY_START_MAINTENANCE = 2153
