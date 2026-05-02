"""Tests für Senior Code Review Heuristiken."""
from __future__ import annotations

import sys
from pathlib import Path

# sys.path anpassen, damit die Tests auch direkt aufrufbar sind
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from tools.senior_review import run_senior_review  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------
def test_detects_openai_key(tmp_path: Path) -> None:
    _write(tmp_path, "app/config.py", 'OPENAI_KEY = "sk-abcdefghijklmnopqrstuvwxyz12345678"\n')
    report = run_senior_review(tmp_path)
    rules = {f.rule for f in report.critical}
    assert "secret.openai_key" in rules
    assert report.passed is False


def test_detects_github_token(tmp_path: Path) -> None:
    _write(tmp_path, "server.py", 'TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"\n')
    report = run_senior_review(tmp_path)
    assert any(f.rule == "secret.github_token" for f in report.critical)


def test_detects_generic_hardcoded_secret(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "auth.py",
        'password = "supersecret_prod_value_1234"\n',
    )
    report = run_senior_review(tmp_path)
    assert any(f.rule == "secret.hardcoded" for f in report.critical)


def test_ignores_obvious_placeholders(tmp_path: Path) -> None:
    _write(tmp_path, "config.py", 'api_key = "changeme_changeme_change"\n')
    report = run_senior_review(tmp_path)
    assert not any(f.rule == "secret.hardcoded" for f in report.critical)


# ---------------------------------------------------------------------------
# Silent Failures
# ---------------------------------------------------------------------------
def test_detects_bare_except(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "svc.py",
        "def f() -> None:\n    try:\n        run()\n    except:\n        pass\n",
    )
    report = run_senior_review(tmp_path)
    rules = {f.rule for f in report.critical}
    assert "py.bare_except" in rules


def test_detects_empty_js_catch(tmp_path: Path) -> None:
    _write(tmp_path, "a.ts", "try { run(); } catch (e) {}\n")
    report = run_senior_review(tmp_path)
    assert any(f.rule == "js.empty_catch" for f in report.critical)


# ---------------------------------------------------------------------------
# Dangerous Code
# ---------------------------------------------------------------------------
def test_detects_eval(tmp_path: Path) -> None:
    _write(tmp_path, "bad.py", "def run(x: str) -> None:\n    eval(x)\n")
    report = run_senior_review(tmp_path)
    assert any(f.rule == "py.eval_exec" for f in report.critical)


def test_detects_react_dangerously_set(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "comp.tsx",
        "export function C(){ return <div dangerouslySetInnerHTML={{__html: data}}/> }\n",
    )
    report = run_senior_review(tmp_path)
    assert any(f.rule == "react.dangerously_set_inner_html" for f in report.critical)


# ---------------------------------------------------------------------------
# Quality Findings (MAJOR)
# ---------------------------------------------------------------------------
def test_console_log_is_major(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.ts", "export const x = () => { console.log('x'); };\n")
    report = run_senior_review(tmp_path)
    assert any(f.rule == "js.console_log" for f in report.major)
    # console.log darf mark_complete NICHT blocken
    assert report.passed is True


def test_ts_any_is_major(tmp_path: Path) -> None:
    _write(tmp_path, "src/api.ts", "export function load(x: any): any { return x; }\n")
    report = run_senior_review(tmp_path)
    assert any(f.rule == "ts.any_type" for f in report.major)


def test_todo_is_major(tmp_path: Path) -> None:
    _write(tmp_path, "note.py", "# TODO: implement\ndef noop() -> None:\n    pass\n")
    report = run_senior_review(tmp_path)
    assert any(f.rule == "note.todo" for f in report.major)


def test_print_in_prod_is_major_but_not_in_tests(tmp_path: Path) -> None:
    _write(tmp_path, "svc.py", "def go() -> None:\n    print('hi')\n")
    _write(tmp_path, "tests/test_svc.py", "def test_foo() -> None:\n    print('ok')\n")
    report = run_senior_review(tmp_path)
    prints = [f for f in report.major if f.rule == "py.print_in_prod"]
    assert len(prints) == 1
    assert prints[0].path == "svc.py"


# ---------------------------------------------------------------------------
# Struktur / Ignore-Pfade
# ---------------------------------------------------------------------------
def test_ignores_node_modules_and_dist(tmp_path: Path) -> None:
    _write(tmp_path, "node_modules/lib/index.js", "console.log('noise');\n")
    _write(tmp_path, "dist/bundle.js", "console.log('dist');\n")
    _write(tmp_path, "src/app.js", "export const n = 1;\n")
    report = run_senior_review(tmp_path)
    assert report.files_reviewed == 1


def test_clean_codebase_passes(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "app/service.py",
        "from __future__ import annotations\n"
        "import logging\n"
        "logger = logging.getLogger(__name__)\n\n"
        "def greet(name: str) -> str:\n"
        '    """Return a greeting."""\n'
        "    return f\"Hello {name}\"\n",
    )
    report = run_senior_review(tmp_path)
    assert report.passed is True
    assert len(report.critical) == 0


def test_report_render_contains_verdict(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'key = "sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n')
    report = run_senior_review(tmp_path)
    out = report.render()
    assert "SENIOR CODE REVIEW REPORT" in out
    assert "BLOCKED" in out
    assert "secret.openai_key" in out


def test_summary_dict_shape(tmp_path: Path) -> None:
    _write(tmp_path, "b.py", "def f(x): return x\n")
    d = run_senior_review(tmp_path).to_summary_dict()
    assert set(d.keys()) >= {"passed", "files_reviewed", "counts", "critical", "major", "minor"}
    assert set(d["counts"].keys()) == {"critical", "major", "minor"}
