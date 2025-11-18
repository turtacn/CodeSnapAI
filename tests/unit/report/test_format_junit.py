from __future__ import annotations
import pytest
from lxml import etree
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, Issue, IssueLocation
from codesage.report.format_junit import render_junit_xml


def test_junit_xml_contains_failures():
    snapshot = ProjectSnapshot(
        metadata={
            "version": "1.0",
            "timestamp": "2023-01-01T00:00:00",
            "project_name": "test",
            "file_count": 1,
            "total_size": 1024,
            "tool_version": "0.1.0",
            "config_hash": "abc"
        },
        files=[
            FileSnapshot(
                path="file1.py",
                language="python",
                issues=[
                    Issue(rule_id="E001", severity="error", message="Error 1", location=IssueLocation(file_path="file1.py", line=10)),
                ],
            )
        ],
    )

    junit_xml = render_junit_xml(snapshot)
    root = etree.fromstring(junit_xml.encode('utf-8'))

    assert root.tag == "testsuite"
    assert root.get("tests") == "1"
    assert root.get("failures") == "1"

    testcase = root.find("testcase")
    assert testcase is not None
    assert testcase.get("classname") == "file1.py"
    assert testcase.get("name") == "E001:10"

    failure = testcase.find("failure")
    assert failure is not None
    assert "E001 - Error 1" in failure.get("message")
