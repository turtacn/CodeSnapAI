from pathlib import Path
from typing import List
import json
from datetime import datetime, UTC

from codesage.policy.engine import PolicyDecision
from codesage.history.regression_detector import RegressionWarning

def export_policy_decisions(decisions: List[PolicyDecision], export_dir: Path) -> None:
    """Exports a list of policy decisions to a directory."""
    export_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    file_path = export_dir / f"policy_decisions_{ts}.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump([d.model_dump(mode='json') for d in decisions], f, indent=2)

def export_regression_warnings(warnings: List[RegressionWarning], export_dir: Path) -> None:
    """Exports a list of regression warnings to a directory."""
    export_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    file_path = export_dir / f"regression_warnings_{ts}.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump([w.model_dump(mode='json') for w in warnings], f, indent=2)
