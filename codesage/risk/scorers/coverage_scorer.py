import xml.etree.ElementTree as ET
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class CoverageScorer:
    """
    Parses coverage reports (e.g., Cobertura XML) and provides coverage metrics.
    """
    def __init__(self, coverage_file: Optional[str] = None):
        self.coverage_file = coverage_file
        self.coverage_data: Dict[str, float] = {} # file_path -> coverage_percentage (0.0 to 1.0)
        self._is_parsed = False

    def parse(self):
        if not self.coverage_file:
            return

        try:
            tree = ET.parse(self.coverage_file)
            root = tree.getroot()

            # Cobertura format: <class filename="path/to/file.py" line-rate="0.8">
            # We iterate over packages -> classes -> class

            for package in root.findall(".//package"):
                for cls in package.findall(".//class"):
                    filename = cls.get("filename")
                    line_rate = cls.get("line-rate")

                    if filename and line_rate:
                        try:
                            rate = float(line_rate)
                            self.coverage_data[filename] = rate
                        except ValueError:
                            pass

            self._is_parsed = True

        except ET.ParseError as e:
            logger.error(f"Failed to parse coverage file {self.coverage_file}: {e}")
        except FileNotFoundError:
            logger.warning(f"Coverage file {self.coverage_file} not found.")

    def get_coverage(self, file_path: str) -> float:
        """
        Returns coverage rate for the file (0.0 to 1.0).
        Returns 1.0 (assumed covered) if no report is available to avoid penalizing when no data exists,
        OR returns 0.0 if we want to be strict.
        Given the requirement: "Coverage penalty amplifies static risk", it implies if we HAVE coverage data
        and it is low, we penalize. If we don't have coverage data, maybe we shouldn't penalize?
        However, the formula is `w3 * (1 - Coverage)`.
        If no coverage data, and we return 0.0, the penalty is max.
        If we return 1.0, the penalty is 0.

        Usually, if coverage is missing, we assume 0 for that file if the report exists.
        If the report doesn't exist at all, we might want to return 1.0 to disable this factor.
        """
        if not self._is_parsed and self.coverage_file:
            self.parse()

        if not self.coverage_data:
            # No data loaded or file not found.
            # To avoid mass false positives when no coverage report is generated, return 1.0?
            # Or should we require the user to provide it?
            # The prompt says: "若提供覆盖率报告，...". Implies optional.
            return 1.0

        # Try to match file path. The coverage report usually has relative paths.
        # We might need fuzzy matching or normalization.
        # For now, exact match or simple suffix match.

        if file_path in self.coverage_data:
            return self.coverage_data[file_path]

        # Try finding by suffix if exact match fails (e.g. src/main.py vs main.py)
        for cov_path, rate in self.coverage_data.items():
            if file_path.endswith(cov_path) or cov_path.endswith(file_path):
                return rate

        # If file is not in the report but report exists, it usually means 0 coverage.
        return 0.0
