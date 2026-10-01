import importlib.machinery
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

TOOLS_PATH = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS_PATH))

from modulefinder import ModuleFinder

import python_dependency_analyzer as analyzer_module
from python_dependency_analyzer import (
    PythonDependencyAnalyzer,
    _DiagnosticModuleFinder,
)


def test_finds_project_python_files_only(tmp_path, monkeypatch):
    src_path = tmp_path / "src"
    entrypoint = src_path / "thermo_ui_app.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.touch()
    local_module = src_path / "server" / "api_routes.py"
    local_module.parent.mkdir()
    local_module.touch()
    external_module = tmp_path / "site-packages" / "dependency.py"
    external_module.parent.mkdir()
    external_module.touch()

    class FakeModuleFinder:
        def __init__(self):
            self.modules = {
                "app": SimpleNamespace(__file__=str(entrypoint)),
                "local": SimpleNamespace(__file__=str(local_module)),
                "external": SimpleNamespace(__file__=str(external_module)),
                "builtin": SimpleNamespace(__file__=None),
            }

        def run_script(self, _entrypoint):
            pass

    monkeypatch.setattr(analyzer_module, "_DiagnosticModuleFinder", FakeModuleFinder)
    analyzer = PythonDependencyAnalyzer(tmp_path)

    analyzer.find_local_python_files()

    assert analyzer.python_files == {entrypoint.resolve(), local_module.resolve()}


def test_diagnostic_finder_names_namespace_package(monkeypatch):
    def raise_attribute_error(_self, _name, _path, _parent=None):
        raise AttributeError("loader is None")

    monkeypatch.setattr(ModuleFinder, "find_module", raise_attribute_error)
    monkeypatch.setattr(
        importlib.machinery.PathFinder,
        "find_spec",
        staticmethod(lambda _name, _path=None: SimpleNamespace(loader=None)),
    )

    finder = _DiagnosticModuleFinder()
    parent = SimpleNamespace(__name__="parent")

    with pytest.raises(AttributeError, match="namespace package 'parent.config'"):
        finder.find_module("config", [], parent)


def test_extract_imports_excludes_local_and_standard_library(tmp_path):
    src_path = tmp_path / "src"
    server_path = src_path / "server"
    config_path = src_path / "config"
    server_path.mkdir(parents=True)
    config_path.mkdir(parents=True)
    route_file = server_path / "api_routes.py"
    route_file.write_text(
        """
import json
import fastapi
from fastapi import APIRouter
from config.settings import settings
from server.schedule_dto import ScheduleData
""",
        encoding="utf-8",
    )
    local_files = {
        route_file,
        server_path / "__init__.py",
        server_path / "schedule_dto.py",
        config_path / "__init__.py",
        config_path / "settings.py",
    }
    analyzer = PythonDependencyAnalyzer(tmp_path)
    analyzer.python_files = {path.resolve() for path in local_files}

    imports = analyzer.extract_imports(route_file)

    assert imports == {"fastapi"}


def test_find_asset_files_tracks_resolved_and_missing_html(tmp_path):
    source_file = tmp_path / "src" / "server" / "web_routes.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        'PAGE = "client/index.html"\nMISSING = "client/missing.html"\n',
        encoding="utf-8",
    )
    html_file = tmp_path / "src" / "client" / "index.html"
    html_file.parent.mkdir(parents=True)
    html_file.write_text("<html></html>", encoding="utf-8")
    analyzer = PythonDependencyAnalyzer(tmp_path)
    analyzer.python_files = {source_file.resolve()}

    analyzer.find_asset_files()

    assert analyzer.asset_files == {html_file.resolve()}
    assert analyzer.missing_references == [(source_file.resolve(), "client/missing.html")]


def test_minimal_requirements_preserves_matching_requirement_lines(tmp_path):
    requirements_file = tmp_path / "requirements.txt"
    requirements_file.write_text(
        "fastapi[standard]>=0.104\npydantic==2.7.0\n"
        "pydantic-settings==2.14.2\nhttpx>=0.25\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "requirements-minimal.txt"
    analyzer = PythonDependencyAnalyzer(tmp_path)
    analyzer.external_imports = {"fastapi", "pydantic_settings", "httpx"}

    used_requirements = analyzer.get_used_requirements(requirements_file)
    analyzer.generate_requirements_minimal(output_file, used_requirements)

    assert used_requirements == [
        "fastapi[standard]>=0.104",
        "pydantic-settings==2.14.2",
        "httpx>=0.25",
    ]
    assert output_file.read_text(encoding="utf-8") == (
        "fastapi[standard]>=0.104\npydantic-settings==2.14.2\nhttpx>=0.25\n"
    )