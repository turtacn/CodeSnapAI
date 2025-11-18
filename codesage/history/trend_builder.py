from pathlib import Path
from typing import List

from codesage.history.models import SnapshotIndex
from codesage.history.store import load_historical_snapshot, load_snapshot_index
from codesage.history.trend_models import TrendPoint, TrendSeries


def build_trend_series(root: Path, project: str) -> TrendSeries:
    """Builds a trend series from historical snapshots."""
    index = load_snapshot_index(root, project)
    points: List[TrendPoint] = []

    # Sort by creation time to ensure the trend is chronological
    sorted_items = sorted(index.items, key=lambda m: m.created_at)

    for meta in sorted_items:
        try:
            hs = load_historical_snapshot(root, project, meta.snapshot_id)
            snap = hs.snapshot

            high_risk = sum(1 for f in snap.files if getattr(f.risk, "level", "low") == "high")
            total_issues = sum(len(f.issues) for f in snap.files)
            error_issues = sum(1 for f in snap.files for i in f.issues if i.severity == "error")

            point = TrendPoint(
                snapshot_id=meta.snapshot_id,
                created_at=meta.created_at,
                high_risk_files=high_risk,
                total_issues=total_issues,
                error_issues=error_issues,
            )
            points.append(point)
        except FileNotFoundError:
            # Log this in a real application
            print(f"Warning: Snapshot file for {meta.snapshot_id} not found, skipping.")
            continue


    return TrendSeries(project_name=project, points=points)
