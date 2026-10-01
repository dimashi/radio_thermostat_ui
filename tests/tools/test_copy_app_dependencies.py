import sys
from pathlib import Path
from unittest.mock import Mock

TOOLS_PATH = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS_PATH))

from copy_app_dependencies import DependencyAnalyzer


def test_find_html_files_delegates_between_analyzers(tmp_path):
    html_asset = tmp_path / "src" / "client" / "index.html"
    stylesheet = tmp_path / "src" / "client" / "site.css"
    python_analyzer = Mock()
    python_analyzer.asset_files = {html_asset}
    html_analyzer = Mock()
    html_analyzer.dependency_files = {html_asset, stylesheet}
    analyzer = DependencyAnalyzer(tmp_path, python_analyzer, html_analyzer)

    analyzer.find_html_files()

    python_analyzer.find_asset_files.assert_called_once_with()
    html_analyzer.find_dependencies.assert_called_once_with({html_asset})
    assert analyzer.html_files == {html_asset, stylesheet}


def test_generate_artifacts_list_combines_analyzer_results(tmp_path):
    python_file = tmp_path / "src" / "server.py"
    html_file = tmp_path / "src" / "client" / "index.html"
    python_analyzer = Mock()
    python_analyzer.python_files = {python_file}
    analyzer = DependencyAnalyzer(tmp_path, python_analyzer, Mock())
    analyzer.html_files = {html_file}

    artifacts = analyzer.generate_artifacts_list(tmp_path / "artifacts.txt")

    assert artifacts == ["src/server.py", "src/client/index.html"]


def test_run_orchestrates_analyzers_and_generates_minimal_requirements(tmp_path):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    requirements_file = tmp_path / "requirements.txt"
    requirements_file.write_text("fastapi>=0.100\n", encoding="utf-8")
    python_file = tmp_path / "src" / "server.py"
    html_file = tmp_path / "src" / "client" / "index.html"

    python_analyzer = Mock()
    python_analyzer.python_files = {python_file}
    python_analyzer.asset_files = {html_file}
    python_analyzer.external_imports = {"fastapi"}
    python_analyzer.missing_references = []
    python_analyzer.get_used_requirements.return_value = ["fastapi>=0.100"]

    html_analyzer = Mock()
    html_analyzer.dependency_files = {html_file}
    html_analyzer.missing_references = []
    analyzer = DependencyAnalyzer(tmp_path, python_analyzer, html_analyzer)
    analyzer.copy_to_dist = Mock()

    analyzer.run()

    python_analyzer.find_local_python_files.assert_called_once_with()
    python_analyzer.analyze_python_imports.assert_called_once_with()
    python_analyzer.find_asset_files.assert_called_once_with()
    html_analyzer.find_dependencies.assert_called_once_with({html_file})
    python_analyzer.get_used_requirements.assert_called_once_with(requirements_file)
    python_analyzer.generate_requirements_minimal.assert_called_once_with(
        build_dir / ".dist" / "requirements-minimal.txt", ["fastapi>=0.100"]
    )
    analyzer.copy_to_dist.assert_called_once_with(
        ["src/server.py", "src/client/index.html"]
    )


def test_copy_to_dist_copies_only_listed_artifacts(tmp_path):
    artifact = tmp_path / "src" / "server.py"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("app = True\n", encoding="utf-8")
    requirements = tmp_path / "build" / "requirements-minimal.txt"
    requirements.parent.mkdir()
    requirements.write_text("fastapi>=0.100\n", encoding="utf-8")
    dist_dir = tmp_path / "build" / ".dist"
    dist_dir.mkdir()
    (dist_dir / "stale.txt").write_text("stale", encoding="utf-8")
    analyzer = DependencyAnalyzer(tmp_path, Mock(), Mock())

    analyzer.copy_to_dist(["src/server.py"])

    assert (dist_dir / "src" / "server.py").read_text(encoding="utf-8") == "app = True\n"
    assert not (dist_dir / "requirements-minimal.txt").exists()
    assert not (dist_dir / "stale.txt").exists()