
import pytest
import os
import xml.etree.ElementTree as ET
from codesage.test.coverage_parser import CoverageParser

class TestCoverageParser:

    def test_parse_cobertura(self, tmp_path):
        xml_content = """<?xml version="1.0" ?>
        <coverage>
            <packages>
                <package>
                    <classes>
                        <class filename="src/foo.py" line-rate="0.8"/>
                        <class filename="src/bar.py" line-rate="0.5"/>
                    </classes>
                </package>
            </packages>
        </coverage>
        """
        f = tmp_path / "coverage.xml"
        f.write_text(xml_content)

        parser = CoverageParser(str(f))

        assert parser.get_file_coverage("src/foo.py") == 0.8
        assert parser.get_file_coverage("src/bar.py") == 0.5
        assert parser.get_file_coverage("unknown.py") is None

    def test_parse_jacoco(self, tmp_path):
        xml_content = """<?xml version="1.0" ?>
        <report>
            <package name="com/example">
                <sourcefile name="Main.java">
                    <counter type="INSTRUCTION" missed="100" covered="50"/>
                    <counter type="LINE" missed="5" covered="5"/>
                </sourcefile>
            </package>
        </report>
        """
        f = tmp_path / "jacoco.xml"
        f.write_text(xml_content)

        parser = CoverageParser(str(f))

        # Covered 5, Missed 5 => Total 10 => 0.5
        assert parser.get_file_coverage("com/example/Main.java") == 0.5

    def test_parse_go_cover(self, tmp_path):
        content = """mode: set
github.com/pkg/foo/bar.go:10.12,12.3 2 1
github.com/pkg/foo/baz.go:5.1,6.1 10 0
"""
        f = tmp_path / "coverage.out"
        f.write_text(content)

        parser = CoverageParser(str(f))

        # bar.go: 2 stmts, covered
        assert parser.get_file_coverage("github.com/pkg/foo/bar.go") == 1.0
        # baz.go: 10 stmts, not covered
        assert parser.get_file_coverage("github.com/pkg/foo/baz.go") == 0.0

    def test_get_uncovered_files(self, tmp_path):
        xml_content = """<?xml version="1.0" ?>
        <coverage>
             <packages>
                <package>
                    <classes>
                        <class filename="covered.py" line-rate="1.0"/>
                        <class filename="uncovered.py" line-rate="0.0"/>
                    </classes>
                </package>
            </packages>
        </coverage>
        """
        f = tmp_path / "coverage.xml"
        f.write_text(xml_content)

        parser = CoverageParser(str(f))
        uncovered = parser.get_uncovered_files()

        assert "uncovered.py" in uncovered
        assert "covered.py" not in uncovered
