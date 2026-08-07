from __future__ import annotations

from pathlib import Path


class BaseDependencyAnalyzer:
    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()
        self.src_path = self.root_path / "src"

    def _resolve_reference(self, ref: str, search_subdir: str) -> Path | None:
        """Resolve a referenced file under the project tree."""
        ref_path = Path(ref)
        candidates = []

        search_root = self.src_path / search_subdir

        if ref.startswith(search_subdir):
            candidates.append(search_root / ref[len(search_subdir):])
        candidates.append(search_root / ref)
        candidates.append(self.src_path / ref)
        candidates.append(self.root_path / ref)

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.exists() and resolved.is_file():
                return resolved

        if ref_path.name:
            matches = list(search_root.rglob(ref_path.name))
            if matches:
                return matches[0].resolve()

        return None
