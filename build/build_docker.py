#!/usr/bin/env python3
"""
Docker packaging script that:
1. Analyzes Python imports starting from controller.py
2. Tracks HTML files and their references
3. Determines minimal dependencies
4. Creates .dist folder with only necessary files for Docker build
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import Set, Dict, List
from collections import defaultdict


class DependencyAnalyzer:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.server_path = root_path / "server"
        self.client_path = root_path / "client"
        self.python_files: Set[Path] = set()
        self.html_files: Set[Path] = set()
        self.local_modules: Set[str] = set()
        self.external_imports: Set[str] = set()
        self.processed_modules: Set[str] = set()

    def find_local_python_files(self):
        """Find all Python files in server directory."""
        for py_file in self.server_path.glob("*.py"):
            if not py_file.name.startswith("__"):
                self.python_files.add(py_file)
                # Extract module name
                self.local_modules.add(py_file.stem)

    def extract_imports(self, file_path: Path) -> Set[str]:
        """Extract top-level imports from a Python file."""
        imports = set()
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split(".")[0]
                        imports.add(module_name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split(".")[0]
                        imports.add(module_name)
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
        
        return imports

    def analyze_python_imports(self):
        """Recursively analyze all Python imports."""
        controller_file = self.server_path / "controller.py"
        
        to_process = {controller_file}
        while to_process:
            current_file = to_process.pop()
            if current_file in self.processed_modules:
                continue
            
            self.processed_modules.add(current_file)
            imports = self.extract_imports(current_file)
            
            for import_name in imports:
                if import_name in self.local_modules:
                    # Local module, add to processing queue
                    module_file = self.server_path / f"{import_name}.py"
                    if module_file.exists() and module_file not in self.processed_modules:
                        to_process.add(module_file)
                else:
                    # External import
                    self.external_imports.add(import_name)

    def find_html_files(self):
        """Find all HTML files referenced in FileResponse calls."""
        # Scan all Python files for FileResponse calls
        for py_file in self.python_files:
            self._extract_fileresponse_paths(py_file)

        # Recursively find referenced files in HTMLs
        self._scan_html_references()

    def _extract_fileresponse_paths(self, file_path: Path):
        """Extract file paths from FileResponse() calls in Python files."""
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            # Find all FileResponse calls: FileResponse(something)
            fileresponse_matches = re.finditer(r'FileResponse\s*\(\s*([^)]+)\s*\)', content)
            
            for match in fileresponse_matches:
                arg = match.group(1).strip()
                
                # Try to resolve the path
                resolved_path = self._resolve_path_argument(arg, content, file_path)
                if resolved_path and resolved_path.exists() and resolved_path.suffix in ['.html', '.htm']:
                    self.html_files.add(resolved_path)
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")

    def _resolve_path_argument(self, arg: str, file_content: str, file_path: Path) -> Path:
        """Resolve a FileResponse argument to an actual path.
        
        Handles:
        - String literals: FileResponse("path/to/file.html")
        - Variables: FileResponse(html_path) where html_path = ...
        
        Paths are resolved relative to the repository root.
        """
        # Case 1: String literal
        string_match = re.match(r'^["\']([^"\']+)["\']$', arg)
        if string_match:
            path_str = string_match.group(1)
            # Resolve relative to repo root
            resolved = (self.root_path / path_str).resolve()
            if resolved.exists():
                return resolved
            return None
        
        # Case 2: Variable reference - try to find its definition
        var_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)$', arg)
        if var_match:
            var_name = var_match.group(1)
            # Look for: var_name = ... in the file
            var_pattern = rf'{var_name}\s*=\s*(.+?)(?:\n|$)'
            var_match_in_content = re.search(var_pattern, file_content, re.MULTILINE)
            if var_match_in_content:
                var_value = var_match_in_content.group(1).strip()
                # Recursively resolve the variable's value
                return self._resolve_path_argument(var_value, file_content, file_path)
        
        return None

    def _scan_html_references(self):
        """Find all files referenced in HTML files (scripts, links, etc)."""
        for html_file in list(self.html_files):
            try:
                with open(html_file, "r") as f:
                    content = f.read()
                    
                    # Find script sources (but exclude CDN URLs)
                    script_srcs = re.findall(r'src="([^"]+)"', content)
                    for src in script_srcs:
                        if not src.startswith(('http://', 'https://', 'file://')):
                            ref_path = (html_file.parent / src).resolve()
                            if ref_path.exists():
                                if ref_path.suffix in ['.js', '.css']:
                                    self.html_files.add(ref_path)
                    
                    # Find stylesheet links
                    link_hrefs = re.findall(r'href="([^"]+)"', content)
                    for href in link_hrefs:
                        if not href.startswith(('http://', 'https://', 'file://')):
                            ref_path = (html_file.parent / href).resolve()
                            if ref_path.exists():
                                if ref_path.suffix in ['.css', '.js']:
                                    self.html_files.add(ref_path)
            except Exception as e:
                print(f"Warning: Could not parse {html_file}: {e}")

    def get_used_requirements(self, requirements_file: Path) -> List[str]:
        """Filter requirements.txt to only include used packages."""
        with open(requirements_file, "r") as f:
            all_requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        used_requirements = []
        for req in all_requirements:
            # Extract base package name (handle version specs and extras like uvicorn[standard])
            # Remove extras: uvicorn[standard] -> uvicorn
            package_name = req.split("[")[0]
            # Remove version: uvicorn==0.24.0 -> uvicorn
            package_name = re.split(r'[<>=!]', package_name)[0].strip().lower()
            
            if package_name in self.external_imports:
                used_requirements.append(req)
        
        return used_requirements

    def generate_artifacts_list(self, output_path: Path):
        """Generate list of all necessary artifacts (py, html, css, js) for deployment."""
        artifacts = []
        
        # Add Python files
        for py_file in sorted(self.python_files):
            artifacts.append(f"server/{py_file.name}")
        
        # Add HTML/CSS/JS files
        for artifact in sorted(self.html_files):
            rel_path = artifact.relative_to(self.root_path)
            artifacts.append(str(rel_path))
        
        with open(output_path, "w") as f:
            for artifact in artifacts:
                f.write(f"{artifact}\n")
        
        print(f"[+] Generated {output_path}")
        return artifacts

    def copy_to_dist(self, artifacts: List[str], used_requirements: List[str]):
        """Copy artifacts and requirements to build/.dist folder for Docker build."""
        dist_dir = self.root_path / "build" / ".dist"
        
        # Clean and create .dist directory
        if dist_dir.exists():
            import shutil
            shutil.rmtree(dist_dir)
        dist_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy each artifact, preserving directory structure
        for artifact in artifacts:
            src_path = self.root_path / artifact
            if src_path.exists():
                # Create subdirectory if needed
                dest_path = dist_dir / artifact
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(src_path, dest_path)
        
        # Copy requirements-minimal.txt
        req_file = self.root_path / "build" / "requirements-minimal.txt"
        if req_file.exists():
            import shutil
            shutil.copy2(req_file, dist_dir / "requirements-minimal.txt")
        
        print(f"[+] Created {dist_dir} with artifacts and requirements")

    def generate_requirements_minimal(self, output_path: Path, used_requirements: List[str]):
        """Generate minimal requirements.txt."""
        with open(output_path, "w") as f:
            f.write("\n".join(used_requirements) + "\n")
        
        print(f"[+] Generated {output_path}")

    def print_analysis(self):
        """Print analysis results."""
        print("\n" + "="*60)
        print("DEPENDENCY ANALYSIS REPORT")
        print("="*60)
        
        print(f"\nPython Files Found ({len(self.python_files)}):")
        for pf in sorted(self.python_files):
            print(f"  - {pf.relative_to(self.root_path)}")
        
        print(f"\nHTML/Static Files Found ({len(self.html_files)}):")
        for hf in sorted(self.html_files):
            print(f"  - {hf.relative_to(self.root_path)}")
        
        print(f"\nLocal Modules Referenced: {sorted(self.local_modules)}")
        print(f"\nExternal Imports Detected: {sorted(self.external_imports)}")
        
        print("\n" + "="*60)

    def run(self):
        """Execute full analysis."""
        print("[*] Analyzing dependencies...")
        
        self.find_local_python_files()
        self.analyze_python_imports()
        self.find_html_files()
        
        self.print_analysis()
        
        # Generate requirements - read from project root
        requirements_file = self.root_path / "requirements.txt"
        used_reqs = self.get_used_requirements(requirements_file)
        
        print(f"\n[+] Used Requirements ({len(used_reqs)}):")
        for req in used_reqs:
            print(f"  - {req}")
        
        # Generate outputs 
        artifacts = []
        for py_file in sorted(self.python_files):
            artifacts.append(f"server/{py_file.name}")
        for artifact in sorted(self.html_files):
            rel_path = artifact.relative_to(self.root_path)
            artifacts.append(str(rel_path))
        
        self.generate_requirements_minimal(self.root_path / "build" / "requirements-minimal.txt", used_reqs)
        self.copy_to_dist(artifacts, used_reqs)
        
        print("\n[+] Build analysis complete!")
        print("\nGenerated files:")
        print("  - build/requirements-minimal.txt: Minimal Python dependencies")
        print("  - build/.dist/: Directory with all files needed for Docker build")
        print("\nNext steps:")
        print("  1. Build: docker build -f build/Dockerfile -t radio-thermostat-ui .")
        print("  2. Run: docker run -p 8080:8080 radio-thermostat-ui")


if __name__ == "__main__":
    # Get project root (parent of build folder)
    root = Path(__file__).parent.parent
    analyzer = DependencyAnalyzer(root)
    analyzer.run()
