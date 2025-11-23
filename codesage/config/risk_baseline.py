from pydantic import BaseModel

class RiskBaselineConfig(BaseModel):
    """Configuration for the baseline risk scorer."""

    # Weights for risk scoring (Base static score)
    weight_complexity_max: float = 0.4
    weight_complexity_avg: float = 0.3
    weight_fan_out: float = 0.2
    weight_loc: float = 0.1

    # Weights for multi-dimensional scoring
    # Final = w_static * static + w_churn * churn + w_cov * (static * (1-cov))
    # Or as per task: Score = w1 * Complexity + w2 * Churn + w3 * (1 - Coverage)
    # The "Complexity" here refers to the static score calculated above.

    weight_static_score: float = 0.5
    weight_churn: float = 0.3
    weight_coverage_penalty: float = 0.2

    # Propagation
    propagation_factor: float = 0.2
    propagation_iterations: int = 5

    # Thresholds for complexity and risk levels
    threshold_complexity_high: int = 10
    threshold_risk_medium: float = 0.4
    threshold_risk_high: float = 0.7

    # Churn settings
    churn_since_days: int = 90
    threshold_churn_high: int = 10 # If file changed > 10 times in 90 days, normalized churn = 1.0

    @classmethod
    def from_defaults(cls) -> "RiskBaselineConfig":
        return cls()
