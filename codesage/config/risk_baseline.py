from pydantic import BaseModel

class RiskBaselineConfig(BaseModel):
    """Configuration for the baseline risk scorer."""

    # Weights for risk scoring
    weight_complexity_max: float = 0.4
    weight_complexity_avg: float = 0.3
    weight_fan_out: float = 0.2
    weight_loc: float = 0.1

    # Thresholds for complexity and risk levels
    threshold_complexity_high: int = 10
    threshold_risk_medium: float = 0.4
    threshold_risk_high: float = 0.7

    @classmethod
    def from_defaults(cls) -> "RiskBaselineConfig":
        return cls()
