from pydantic import BaseModel


class TurbinePoint(BaseModel):
    timestamp: str
    wind_speed: float
    active_power_kw: float
    theoretical_power_kw: float
    deviation_pct: float  # deviation_norm * 100 -- API contract differs from the internal column name on purpose
    in_range: bool
    is_anomaly: bool
