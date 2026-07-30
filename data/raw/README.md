# Raw dataset

**Source:** [Wind Turbine SCADA Dataset](https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset)
on Kaggle. Real SCADA data from a wind turbine in Turkey, 2018, 10-minute intervals.

## How to get it

1. Log into Kaggle and download `T1.csv` from the link above.
2. Place it at `data/raw/T1.csv`.

The file is gitignored (~4 MB, licensed dataset — not redistributed in this repo).

## Expected shape

- 50,531 lines (1 header + 50,530 rows)
- Columns: `Date/Time`, `LV ActivePower (kW)`, `Wind Speed (m/s)`,
  `Theoretical_Power_Curve (KWh)`, `Wind Direction (°)`

## Date format gotcha

`Date/Time` values look like `31 12 2018 23:50` — **day first**, not month first.
Confirmed by finding a `31 12 2018` row: 31 can never be a month, so the first
number must be the day. pandas' default date guessing assumes month-first and
will misparse (or crash on) this format — must pass `format='%d %m %Y %H:%M'`
explicitly when loading.
