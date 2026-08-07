from __future__ import annotations

import re
from pathlib import Path

from base_dependency_analyzer import BaseDependencyAnalyzer


class HtmlDependencyAnalyzer(BaseDependencyAnalyzer):
    def __init__(self, root_path: Path):
        super().__init__(root_path)
        self.dependency_files: set[Path] = set()
        self.missing_references: list[tuple[Path, str]] = []

    def find_dependencies(self, asset_files: set[Path]):
        """Find local file dependencies referenced from HTML files."""
        self.dependency_files.update(asset_files)
        for html_file in asset_files:
            if html_file.suffix.lower() != ".html":
                continue
            self._collect_html_dependencies(html_file)

    def _collect_html_dependencies(self, html_file: Path):
        """Collect local files referenced from an HTML file."""
        try:
            with open(html_file, "r", encoding="utf-8") as handle:
                content = handle.read()
        except (OSError, SyntaxError):
            return

        for attr_name in ("src", "href"):
            for match in re.finditer(rf'{attr_name}="([^"]+)"', content):
                ref = match.group(1).strip()
                if ref.startswith(("http://", "https://", "file://", "data:")):
                    continue

                resolved = self._resolve_reference(ref, "client/")
                if resolved:
                    self.dependency_files.add(resolved)
