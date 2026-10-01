import sys
from pathlib import Path

TOOLS_PATH = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS_PATH))

from html_dependency_analyzer import HtmlDependencyAnalyzer


def test_finds_local_src_and_href_dependencies(tmp_path):
    client_dir = tmp_path / "src" / "client"
    page = client_dir / "pages" / "index.html"
    stylesheet = client_dir / "css" / "site.css"
    script = client_dir / "js" / "app.js"
    page.parent.mkdir(parents=True)
    stylesheet.parent.mkdir(parents=True)
    script.parent.mkdir(parents=True)
    page.write_text(
        '<link href="css/site.css"><script src="js/app.js"></script>',
        encoding="utf-8",
    )
    stylesheet.write_text("body {}", encoding="utf-8")
    script.write_text("console.log('ready');", encoding="utf-8")
    analyzer = HtmlDependencyAnalyzer(tmp_path)

    analyzer.find_dependencies({page})

    assert analyzer.dependency_files == {
        page.resolve(),
        stylesheet.resolve(),
        script.resolve(),
    }
    assert analyzer.missing_references == []


def test_ignores_external_references(tmp_path):
    page = tmp_path / "src" / "client" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(
        '<img src="https://example.com/image.png">'
        '<link href="file:///tmp/site.css">'
        '<script src="data:text/javascript,alert(1)"></script>',
        encoding="utf-8",
    )
    analyzer = HtmlDependencyAnalyzer(tmp_path)

    analyzer.find_dependencies({page})

    assert analyzer.dependency_files == {page.resolve()}
    assert analyzer.missing_references == []


def test_records_missing_local_references(tmp_path):
    page = tmp_path / "src" / "client" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text('<script src="js/missing.js"></script>', encoding="utf-8")
    analyzer = HtmlDependencyAnalyzer(tmp_path)

    analyzer.find_dependencies({page})

    assert analyzer.dependency_files == {page.resolve()}
    assert analyzer.missing_references == [(page.resolve(), "js/missing.js")]


def test_non_html_assets_are_kept_but_not_parsed(tmp_path):
    stylesheet = tmp_path / "src" / "client" / "site.css"
    stylesheet.parent.mkdir(parents=True)
    stylesheet.write_text('body { background: url("missing.png"); }', encoding="utf-8")
    analyzer = HtmlDependencyAnalyzer(tmp_path)

    analyzer.find_dependencies({stylesheet})

    assert analyzer.dependency_files == {stylesheet.resolve()}
    assert analyzer.missing_references == []