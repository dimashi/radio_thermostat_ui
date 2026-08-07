import importlib.util
import tempfile
import textwrap
import unittest
from pathlib import Path


class DependencyAnalyzerTests(unittest.TestCase):
    def test_finds_html_assets_from_python_string_constants_and_html_links(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src" / "client" / "components" / "table_scheduler").mkdir(parents=True)
            (root / "src" / "server").mkdir(parents=True)

            html_file = root / "src" / "client" / "components" / "table_scheduler" / "scheduler.html"
            html_file.write_text(
                '<html><head><link rel="stylesheet" href="styles.css"></head><body><script src="app.js"></script></body></html>',
                encoding="utf-8",
            )
            css_file = root / "src" / "client" / "components" / "table_scheduler" / "styles.css"
            css_file.write_text("body { color: black; }", encoding="utf-8")
            js_file = root / "src" / "client" / "components" / "table_scheduler" / "app.js"
            js_file.write_text("console.log('ok');", encoding="utf-8")

            server_file = root / "src" / "server" / "web_routes.py"
            server_file.write_text(
                textwrap.dedent(
                    """
                    import httpx
                    from pathlib import Path

                    BASE_DIR = Path(__file__).parent.parent

                    PAGE = BASE_DIR / "client/components/table_scheduler/scheduler.html"
                    """
                ),
                encoding="utf-8",
            )

            spec = importlib.util.spec_from_file_location(
                "build_docker",
                Path(__file__).resolve().parents[1] / "build" / "build_docker.py",
            )
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)

            python_analyzer = module.PythonDependencyAnalyzer(root, asset_extensions=(".html", ".css", ".js"))
            python_analyzer.find_local_python_files()
            python_analyzer.find_asset_files()

            html_analyzer = module.HtmlDependencyAnalyzer(root)
            html_analyzer.find_dependencies(python_analyzer.asset_files)

            self.assertEqual(
                html_analyzer.dependency_files,
                {html_file.resolve(), css_file.resolve(), js_file.resolve()},
            )
            self.assertEqual(python_analyzer.external_imports, {"httpx"})


if __name__ == "__main__":
    unittest.main()
