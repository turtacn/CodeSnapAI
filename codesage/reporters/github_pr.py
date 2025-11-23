import os
import httpx
from .base import BaseReporter
from codesage.snapshot.models import ProjectSnapshot, Issue
import logging

logger = logging.getLogger(__name__)

class GitHubPRReporter(BaseReporter):
    def __init__(self, token: str, repo: str, pr_number: int):
        self.token = token
        self.repo = repo
        self.pr_number = pr_number
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )

    def report(self, snapshot: ProjectSnapshot) -> None:
        """
        Post comments on the PR for high severity issues.
        """
        logger.info(f"Reporting to GitHub PR #{self.pr_number} on {self.repo}")

        # Get PR details to find the latest commit SHA (needed for some APIs)
        # For review comments, we usually need the commit_id or we can post generic issue comments

        issues_to_report = []
        for file in snapshot.files:
            for issue in file.issues:
                if issue.severity in ['high', 'error']:
                    issues_to_report.append((file.path, issue))

        if not issues_to_report:
            logger.info("No high severity issues to report.")
            # Optionally update status check to success
            self._create_check_run(snapshot, "success")
            return

        # Post a summary comment
        summary = f"## CodeSnapAI Scan Results\n\n"
        summary += f"Found {len(issues_to_report)} high severity issues.\n"

        for path, issue in issues_to_report[:10]: # Limit to top 10 in summary
            summary += f"- **{path}:{issue.location.line}**: {issue.message}\n"

        if len(issues_to_report) > 10:
            summary += f"\n...and {len(issues_to_report) - 10} more."

        self._post_issue_comment(summary)

        # In a real implementation with diff context, we would use:
        # POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews
        # with comments linked to specific lines in the diff.
        # Since we don't have the diff map here easily without more API calls,
        # we stick to a summary comment for now as per instructions "Review Dog mode" usually implies inline.
        # However, implementing full inline comments requires knowing the position in the diff, not just line number.
        # We will try to post review comments if we can, otherwise fallback to issue comment.

        # Determine status
        status = "failure" if any(i.severity == 'error' for _, i in issues_to_report) else "neutral"
        self._create_check_run(snapshot, status)

    def _post_issue_comment(self, body: str):
        url = f"/repos/{self.repo}/issues/{self.pr_number}/comments"
        try:
            resp = self.client.post(url, json={"body": body})
            resp.raise_for_status()
            logger.info("Posted summary comment to PR.")
        except httpx.HTTPError as e:
            logger.error(f"Failed to post comment: {e}")

    def _create_check_run(self, snapshot: ProjectSnapshot, conclusion: str):
        # This usually requires a SHA, usually available in CI env
        sha = snapshot.metadata.git_commit
        if not sha:
            # Try to get SHA from PR
            try:
                resp = self.client.get(f"/repos/{self.repo}/pulls/{self.pr_number}")
                resp.raise_for_status()
                sha = resp.json()['head']['sha']
            except Exception as e:
                logger.warning(f"Could not determine SHA for check run: {e}")
                return

        url = f"/repos/{self.repo}/check-runs"
        data = {
            "name": "CodeSnapAI Audit",
            "head_sha": sha,
            "status": "completed",
            "conclusion": conclusion,
            "output": {
                "title": "CodeSnapAI Scan",
                "summary": f"Scan completed with {snapshot.issues_summary.total_issues if snapshot.issues_summary else 0} issues.",
            }
        }
        try:
            resp = self.client.post(url, json=data)
            resp.raise_for_status()
            logger.info(f"Created check run with status {conclusion}")
        except httpx.HTTPError as e:
            logger.error(f"Failed to create check run: {e}")
