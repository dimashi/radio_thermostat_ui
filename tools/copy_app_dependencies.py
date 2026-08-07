"""
Docker packaging script that:
1. Finds Python files in the project
2. Scans them for HTML references
3. Matches those references to files under src/client
4. Copies the needed files into build/.dist for Docker
"""

import shutil
import sys
from pathlib import Path

from html_dependency_analyzer import HtmlDependencyAnalyzer
from python_dependency_analyzer import PythonDependencyAnalyzer


class DependencyAnalyzer(PythonDependencyAnalyzer):
    """Backward-compatible wrapper for the old combined analyzer."""

    def __init__(self, root_path: Path):
        super().__init__(root_path)
        self.html_files: set[Path] = set()

    def find_html_files(self):
        self.find_asset_files()
        html_analyzer = HtmlDependencyAnalyzer(self.root_path)
        html_analyzer.find_dependencies(self.asset_files)
        self.html_files = html_analyzer.dependency_files

    def generate_artifacts_list(self, output_path: Path):
        """Generate the list of artifacts needed for deployment."""
        artifacts = []
        for py_file in sorted(self.python_files):
            artifacts.append(str(py_file.relative_to(self.root_path)))
        for artifact in sorted(self.html_files):
            artifacts.append(str(artifact.relative_to(self.root_path)))

        return artifacts

    def copy_to_dist(self, artifacts: list[str]):
        """Copy artifacts and requirements to build/.dist."""
        dist_dir = self.root_path / "build" / ".dist"
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        dist_dir.mkdir(parents=True, exist_ok=True)

        for artifact in artifacts:
            src_path = self.root_path / artifact
            if src_path.exists():
                dest_path = dist_dir / artifact
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)

        req_file = self.root_path / "build" / "requirements-minimal.txt"
        if req_file.exists():
            shutil.copy2(req_file, dist_dir / "requirements-minimal.txt")

    def print_analysis(self):
        """Print analysis results."""
        print("\n" + "=" * 60)
        print("DEPENDENCY ANALYSIS REPORT")
        print("=" * 60)
        print(f"\nPython files found ({len(self.python_files)}):")
        for py_file in sorted(self.python_files):
            print(f"  - {py_file.relative_to(self.root_path)}")
        print(f"\nHTML files found ({len(self.html_files)}):")
        for html_file in sorted(self.html_files):
            print(f"  - {html_file.relative_to(self.root_path)}")
        print(f"\nExternal imports detected: {sorted(self.external_imports)}")
        print("\n" + "=" * 60)

    def run(self):
        """Execute the full analysis."""
        print("[*] Analyzing dependencies...")
        self.find_local_python_files()
        self.analyze_python_imports()
        self.find_html_files()

        if self.missing_references:
            print("\n[!] Build failed: unresolved HTML references detected.")
            for file_path, ref in self.missing_references:
                print(f"  - {file_path.relative_to(self.root_path)}: {ref}")
            sys.exit(1)

        self.print_analysis()

        requirements_file = self.root_path / "requirements.txt"
        used_reqs = self.get_used_requirements(requirements_file)
        self.generate_requirements_minimal(self.root_path / "build" / "requirements-minimal.txt", used_reqs)

        artifacts = self.generate_artifacts_list(self.root_path / "build" / "artifacts.txt")
        self.copy_to_dist(artifacts)

        print("\n[+] Build analysis complete")


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    analyzer = DependencyAnalyzer(root).run()
