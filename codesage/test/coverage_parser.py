"""测试覆盖率解析器
支持多种覆盖率报告格式（对齐 Jules 生态）
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
import logging
import os

logger = logging.getLogger(__name__)

class CoverageParser:
    """覆盖率数据解析器

    支持格式:
    - Cobertura XML (Python/Java 主流)
    - JaCoCo XML (Java)
    - LCOV (JavaScript/Go) - Optional for now
    - Golang cover profile (Go)
    """

    def __init__(self, report_path: str):
        self.report_path = report_path
        self._coverage_cache: Dict[str, float] = {}
        self._parsed = False

        if report_path and os.path.exists(report_path):
            self._parse()

    def _parse(self):
        """Auto-detect and parse the report"""
        if not self.report_path:
            return

        try:
            # Simple heuristic: if ends with .xml, try xml parsers.
            if self.report_path.endswith('.xml'):
                tree = ET.parse(self.report_path)
                root = tree.getroot()
                if root.tag == 'coverage': # Cobertura
                     # Relaxed check: Cobertura usually has packages or sources
                     if 'line-rate' in root.attrib or root.find('packages') is not None or root.find('sources') is not None:
                         self._coverage_cache = self.parse_cobertura(self.report_path)
                elif root.tag == 'report': # JaCoCo
                    self._coverage_cache = self.parse_jacoco(self.report_path)
            # Check for Go cover profile (first line usually "mode: set|count|atomic")
            else:
                 with open(self.report_path, 'r') as f:
                     first_line = f.readline()
                     if first_line.startswith("mode:"):
                         self._coverage_cache = self.parse_go_cover(self.report_path)
        except Exception as e:
            logger.error(f"Failed to parse coverage report {self.report_path}: {e}")

        self._parsed = True

    def parse_go_cover(self, file_path: str) -> Dict[str, float]:
        """解析 Golang cover profile format
        Format: name.go:line.col,line.col num-stmt count
        Example:
        mode: set
        github.com/pkg/foo/bar.go:10.12,12.3 2 1
        """
        results = {}
        file_stats = {} # file -> {statements: int, covered: int}

        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                if line.startswith("mode:"):
                    continue
                parts = line.split()
                if len(parts) < 3:
                    continue

                # Format: file:start,end num-stmt count
                file_segment = parts[0]
                try:
                    stmts = int(parts[1])
                    count = int(parts[2])
                except ValueError:
                    continue

                # Extract filename (everything before the last colon)
                if ':' in file_segment:
                    filename = file_segment.rsplit(':', 1)[0]
                else:
                    filename = file_segment

                if filename not in file_stats:
                    file_stats[filename] = {'total': 0, 'covered': 0}

                file_stats[filename]['total'] += stmts
                if count > 0:
                    file_stats[filename]['covered'] += stmts

            for filename, stats in file_stats.items():
                if stats['total'] > 0:
                    results[filename] = stats['covered'] / stats['total']
                else:
                    results[filename] = 1.0

        except Exception as e:
            logger.error(f"Error parsing Go coverage: {e}")

        return results

    def parse_cobertura(self, xml_path: str) -> Dict[str, float]:
        """解析 Cobertura XML 格式

        返回格式:
        {
            "src/engine.py": 0.85,  # 85% 覆盖率
            "src/parser.py": 0.42,
            ...
        }
        """
        results = {}
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Cobertura structure: packages -> package -> classes -> class -> filename
            for package in root.findall(".//package"):
                for cls in package.findall(".//class"):
                    filename = cls.get("filename")
                    line_rate = cls.get("line-rate")
                    if filename and line_rate:
                        try:
                            results[filename] = float(line_rate)
                        except ValueError:
                            pass

            # Also handle if classes are direct children (some variants)
            for cls in root.findall(".//class"):
                filename = cls.get("filename")
                line_rate = cls.get("line-rate")
                if filename and line_rate:
                     try:
                        results[filename] = float(line_rate)
                     except ValueError:
                        pass

        except Exception as e:
            logger.error(f"Error parsing Cobertura XML: {e}")

        return results

    def parse_jacoco(self, xml_path: str) -> Dict[str, float]:
        """解析 JaCoCo XML 格式（Java 专用）"""
        results = {}
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # JaCoCo structure: package -> sourcefile
            for package in root.findall("package"):
                pkg_name = package.get("name", "")
                for sourcefile in package.findall("sourcefile"):
                    name = sourcefile.get("name")
                    if not name:
                        continue

                    # Construct full path if possible, or just use filename?
                    # Usually report has relative paths.
                    # JaCoCo separates package name (slashes) and file name.
                    full_path = f"{pkg_name}/{name}" if pkg_name else name

                    # Calculate coverage from counters
                    # <counter type="LINE" missed="10" covered="20"/>
                    covered = 0
                    missed = 0
                    found_line_counter = False
                    for counter in sourcefile.findall("counter"):
                        if counter.get("type") == "LINE":
                            try:
                                covered = int(counter.get("covered", 0))
                                missed = int(counter.get("missed", 0))
                                found_line_counter = True
                            except ValueError:
                                pass
                            break

                    if found_line_counter:
                        total = covered + missed
                        if total > 0:
                            results[full_path] = covered / total
                        else:
                            results[full_path] = 1.0 # Empty file?

        except Exception as e:
            logger.error(f"Error parsing JaCoCo XML: {e}")

        return results

    def get_file_coverage(self, file_path: str) -> Optional[float]:
        """查询单个文件的覆盖率（0.0 - 1.0）

        未覆盖返回 None（与"覆盖率为 0"区分）
        """
        # File paths in report might be relative or absolute.
        # We try to match end of path if exact match fails.
        if file_path in self._coverage_cache:
            return self._coverage_cache[file_path]

        # Fuzzy match: try to find if any key in cache ends with file_path (or vice versa)
        # This is risky but common since reports might have different root.
        # Ideally we normalize paths.

        for key, value in self._coverage_cache.items():
            if file_path.endswith(key) or key.endswith(file_path):
                return value

        return None

    def get_uncovered_files(self) -> List[str]:
        """列出完全无测试覆盖的文件（高风险）"""
        return [f for f, cov in self._coverage_cache.items() if cov == 0.0]
