from pydantic import BaseModel, Field

class RiskBaselineConfig(BaseModel):
    """Configuration for the baseline risk scorer."""

    # Weights for risk scoring (Base static score)
    weight_complexity_max: float = 0.4
    weight_complexity_avg: float = 0.3
    weight_fan_out: float = 0.2
    weight_loc: float = 0.1

    # Weights for multi-dimensional scoring (New Model)
    # Risk = w1·Complexity + w2·Churn + w3·(1-Coverage) + w4·AuthorDiversity + w5·FileSize
    weight_complexity: float = Field(default=0.30, description="Weight for complexity score")
    weight_churn: float = Field(default=0.25, description="Weight for git churn score")
    weight_coverage: float = Field(default=0.25, description="Weight for coverage risk")
    weight_author_diversity: float = Field(default=0.10, description="Weight for author diversity")
    weight_file_size: float = Field(default=0.10, description="Weight for file size (LOC)")

    # Legacy weights (kept for backward compatibility if needed, but new model supersedes)
    weight_static_score: float = 0.5
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
    threshold_churn_high: int = 10

    @classmethod
    def from_defaults(cls) -> "RiskBaselineConfig":
        return cls()
