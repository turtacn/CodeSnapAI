from __future__ import annotations
from typing import List
from lxml import etree
from codesage.snapshot.models import ProjectSnapshot
from codesage.report.summary_models import ReportProjectSummary, ReportFileSummary


def render_junit_xml(snapshot: ProjectSnapshot) -> str:
    testsuite = etree.Element("testsuite", name="codesage-analysis")

    total_issues = 0
    failures = 0

    for file in snapshot.files:
        for issue in file.issues:
            total_issues += 1
            testcase = etree.Element("testcase", classname=file.path, name=f"{issue.rule_id}:{issue.location.line}")

            if issue.severity in ["error", "warning"]:
                failures += 1
                failure = etree.Element("failure", message=f"{issue.rule_id} - {issue.message}")
                cdata_content = (
                    f"File: {issue.location.file_path}:{issue.location.line}\n"
                    f"Severity: {issue.severity}\n"
                    f"Rule ID: {issue.rule_id}\n"
                    f"Message: {issue.message}"
                )
                failure.text = etree.CDATA(cdata_content)
                testcase.append(failure)

            testsuite.append(testcase)

    testsuite.set("tests", str(total_issues))
    testsuite.set("failures", str(failures))

    return etree.tostring(testsuite, pretty_print=True, xml_declaration=True, encoding='UTF-8').decode('utf-8')
