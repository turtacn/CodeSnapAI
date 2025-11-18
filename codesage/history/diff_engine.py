from typing import List, Tuple

from codesage.history.diff_models import FileDiffSummary, ProjectDiffSummary
from codesage.snapshot.models import ProjectSnapshot


def diff_project_snapshots(
    old: ProjectSnapshot,
    new: ProjectSnapshot,
    from_id: str,
    to_id: str,
) -> Tuple[ProjectDiffSummary, List[FileDiffSummary]]:
    old_files = {f.path: f for f in old.files}
    new_files = {f.path: f for f in new.files}
    all_paths = sorted(set(old_files.keys()) | set(new_files.keys()))

    file_diffs: List[FileDiffSummary] = []

    high_risk_before = sum(1 for f in old.files if getattr(f.risk, "level", "low") == "high")
    high_risk_after = sum(1 for f in new.files if getattr(f.risk, "level", "low") == "high")

    total_issues_before = sum(len(f.issues) for f in old.files)
    total_issues_after = sum(len(f.issues) for f in new.files)

    error_before = sum(1 for f in old.files for i in f.issues if i.severity == "error")
    error_after = sum(1 for f in new.files for i in f.issues if i.severity == "error")

    for path in all_paths:
        if path not in old_files:
            # New file
            nf = new_files[path]
            fd = FileDiffSummary(
                path=path,
                status="added",
                risk_before=None,
                risk_after=getattr(nf.risk, "level", None) if nf.risk else None,
                risk_score_delta=getattr(nf.risk, "risk_score", 0.0) if nf.risk else 0.0,
                issues_added=len(nf.issues),
                issues_resolved=0,
            )
            file_diffs.append(fd)
            continue

        if path not in new_files:
            # Removed file
            of = old_files[path]
            fd = FileDiffSummary(
                path=path,
                status="removed",
                risk_before=getattr(of.risk, "level", None) if of.risk else None,
                risk_after=None,
                risk_score_delta=-(getattr(of.risk, "risk_score", 0.0) if of.risk else 0.0),
                issues_added=0,
                issues_resolved=len(of.issues),
            )
            file_diffs.append(fd)
            continue

        of = old_files[path]
        nf = new_files[path]

        # Calculate risk level & score delta
        risk_before = getattr(of.risk, "level", None) if of.risk else None
        risk_after = getattr(nf.risk, "level", None) if nf.risk else None
        score_before = getattr(of.risk, "risk_score", 0.0) if of.risk else 0.0
        score_after = getattr(nf.risk, "risk_score", 0.0) if nf.risk else 0.0

        # Issue diff: simple comparison by issue.id
        old_ids = {i.id for i in of.issues}
        new_ids = {i.id for i in nf.issues}
        issues_added = len(new_ids - old_ids)
        issues_resolved = len(old_ids - new_ids)

        status = "modified" if (risk_before != risk_after or issues_added or issues_resolved) else "unchanged"

        fd = FileDiffSummary(
            path=path,
            status=status,
            risk_before=risk_before,
            risk_after=risk_after,
            risk_score_delta=score_after - score_before,
            issues_added=issues_added,
            issues_resolved=issues_resolved,
        )
        file_diffs.append(fd)

    project_diff = ProjectDiffSummary(
        project_name=new.metadata.project_name,
        from_snapshot_id=from_id,
        to_snapshot_id=to_id,
        high_risk_files_delta=high_risk_after - high_risk_before,
        total_issues_delta=total_issues_after - total_issues_before,
        error_issues_delta=error_after - error_before,
    )

    return project_diff, file_diffs
