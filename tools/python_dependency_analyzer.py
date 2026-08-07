from __future__ import annotations

import ast
import re
import sys
from modulefinder import ModuleFinder
from pathlib import Path

from base_dependency_analyzer import BaseDependencyAnalyzer


class PythonDependencyAnalyzer(BaseDependencyAnalyzer):
    def __init__(self, root_path: Path, asset_extensions: map = None):
        super().__init__(root_path)
        if asset_extensions is None:
            self.asset_extensions = {".html": "client/"}
        else:
            self.asset_extensions = asset_extensions
        
        self.python_files: set[Path] = set()
        self.asset_files: set[Path] = set()
        self.external_imports: set[str] = set()
        self.missing_references: list[tuple[Path, str]] = []

    def find_local_python_files(self):
        """Use ModuleFinder like python_finder.py to discover reachable local modules."""
        entrypoint = self.src_path / "thermo_ui_app.py"
        if entrypoint.exists():
            sys.path.insert(0, str(self.src_path))
            finder = ModuleFinder()
            try:
                finder.run_script(str(entrypoint))
            except (FileNotFoundError, ImportError, ModuleNotFoundError):
                pass
            else:
                for mod in finder.modules.values():
                    if not mod.__file__:
                        continue
                    mod_path = Path(mod.__file__).resolve()
                    if str(self.src_path) in str(mod_path):
                        self.python_files.add(mod_path)

                if self.python_files:
                    return

    def extract_imports(self, file_path: Path) -> set[str]:
        """Extract top-level imports from a Python file."""
        imports = set()
        local_module_names = self._get_local_module_names()
        stdlib_module_names = set(sys.stdlib_module_names)

        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split(".")[0]
                        if module_name in local_module_names or module_name in stdlib_module_names:
                            continue
                        imports.add(module_name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_name = node.module.split(".")[0]
                    if module_name in local_module_names or module_name in stdlib_module_names:
                        continue
                    imports.add(module_name)
        except (OSError, SyntaxError):
            pass
        return imports

    def _get_local_module_names(self) -> set[str]:
        """Return local module names resolved under the repository root."""
        local_names: set[str] = set()
        root_path = self.root_path

        for py_file in self.python_files:
            try:
                relative_path = py_file.resolve().relative_to(root_path)
            except ValueError:
                continue

            parts = [part for part in relative_path.parts if part != "__init__.py"]
            if not parts:
                continue

            if parts[-1].endswith(".py"):
                parts = parts[:-1]

            if not parts:
                continue

            for index in range(1, len(parts) + 1):
                local_names.add(".".join(parts[:index]))

        return local_names

    def analyze_python_imports(self):
        """Collect external imports from the discovered Python files."""
        for py_file in self.python_files:
            self.external_imports.update(self.extract_imports(py_file))

    def find_asset_files(self):
        """Find asset references in Python files and collect matching files."""
        for py_file in self.python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as handle:
                    tree = ast.parse(handle.read())
            except (OSError, SyntaxError):
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                ref = node.value.strip()
                for ext, sub_dir in self.asset_extensions.items():
                    if ref.endswith(ext):
                        resolved = self._resolve_reference(ref, sub_dir)
                        if resolved:
                            self.asset_files.add(resolved)
                        else:
                            self.missing_references.append((py_file, ref))

    def get_used_requirements(self, requirements_file: Path) -> list[str]:
        """Filter requirements.txt to only include used packages."""
        with open(requirements_file, "r", encoding="utf-8") as handle:
            all_requirements = [line.strip() for line in handle if line.strip() and not line.startswith("#")]

        used_requirements = []
        for req in all_requirements:
            package_name = req.split("[")[0]
            package_name = re.split(r'[<>=!]', package_name)[0].strip().lower()
            if package_name in self.external_imports:
                used_requirements.append(req)

        return used_requirements

    def generate_requirements_minimal(self, output_path: Path, used_requirements: list[str]):
        """Generate a minimal requirements file."""
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(used_requirements) + "\n")
