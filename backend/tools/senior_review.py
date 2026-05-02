"""
Senior Code Review
==================

Statische Heuristiken, die einen Staff-/Senior-Review simulieren.
Scannt den Workspace und klassifiziert Findings in:

  • CRITICAL : blockiert mark_complete (Secrets, Silent-Failures, eval/SQLi …)
  • MAJOR    : sollte behoben werden (console.log, any, TODO, 80+-Zeilen-Funktionen …)
  • MINOR    : Info (magic numbers, fehlende Docstrings …)

Kein Netzwerk, keine Dependencies außer Standard-Lib. Deterministisch und
schnell genug, um als Gate vor jedem mark_complete zu laufen.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
_EXCLUDED_DIR_PARTS: tuple[str, ...] = (
    ".git", "node_modules", "dist", "build", "__pycache__", ".venv", "venv",
    ".next", ".nuxt", ".turbo", ".cache", "coverage", ".pytest_cache",
    "vendor", "bower_components", ".mypy_cache", ".ruff_cache",
)
_SCAN_EXTENSIONS: tuple[str, ...] = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte",
)
_MAX_FILE_BYTES = 400_000                # überspringt Monster-Files
_MAX_FINDINGS_PER_FILE = 40              # Kappung, damit Report lesbar bleibt


Severity = str  # "critical" | "major" | "minor"


@dataclass
class Finding:
    severity: Severity
    rule: str
    path: str
    line: int
    snippet: str
    hint: str = ""

    def render(self) -> str:
        head = f"  {self.path}:{self.line}  [{self.rule}]"
        body = f"      {self.snippet.strip()[:140]}"
        foot = f"      → {self.hint}" if self.hint else ""
        return "\n".join(s for s in (head, body, foot) if s)


@dataclass
class ReviewReport:
    files_reviewed: int = 0
    lines_reviewed: int = 0
    critical: list[Finding] = field(default_factory=list)
    major: list[Finding] = field(default_factory=list)
    minor: list[Finding] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.critical) == 0

    def render(self) -> str:
        verdict = "✅ PASSED" if self.passed else "❌ BLOCKED"
        lines: list[str] = [
            "🔍 SENIOR CODE REVIEW REPORT",
            "",
            f"Files reviewed : {self.files_reviewed}",
            f"Lines scanned  : {self.lines_reviewed}",
            f"Critical       : {len(self.critical)}",
            f"Major          : {len(self.major)}",
            f"Minor          : {len(self.minor)}",
            "",
        ]

        def _section(title: str, items: list[Finding], limit: int) -> None:
            if not items:
                return
            lines.append(title)
            for f in items[:limit]:
                lines.append(f.render())
            overflow = len(items) - limit
            if overflow > 0:
                lines.append(f"  … und {overflow} weitere")
            lines.append("")

        _section("CRITICAL (blockieren mark_complete):", self.critical, 25)
        _section("MAJOR (sollten behoben werden):",       self.major,    25)
        _section("MINOR (info):",                          self.minor,    15)

        if self.skipped:
            lines.append(f"Übersprungen (zu groß/binär): {len(self.skipped)} Datei(en)")
            lines.append("")

        lines.append(f"VERDICT: {verdict}")
        if not self.passed:
            lines.append(
                "→ Behebe die CRITICAL-Findings und rufe senior_code_review erneut auf."
            )
        return "\n".join(lines)

    def to_summary_dict(self) -> dict:
        def _dump(items: list[Finding]) -> list[dict]:
            return [
                {
                    "rule": f.rule,
                    "path": f.path,
                    "line": f.line,
                    "snippet": f.snippet.strip()[:160],
                    "hint": f.hint,
                }
                for f in items
            ]
        return {
            "passed": self.passed,
            "files_reviewed": self.files_reviewed,
            "counts": {
                "critical": len(self.critical),
                "major": len(self.major),
                "minor": len(self.minor),
            },
            "critical": _dump(self.critical),
            "major": _dump(self.major)[:40],
            "minor": _dump(self.minor)[:40],
        }


# ---------------------------------------------------------------------------
# Regex-Regeln
# ---------------------------------------------------------------------------
# CRITICAL – Secrets (generisch + provider-spezifisch)
_RE_OPENAI_KEY        = re.compile(r"sk-[A-Za-z0-9_\-]{20,}")
_RE_ANTHROPIC_KEY     = re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")
_RE_GITHUB_TOKEN      = re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")
_RE_AWS_SECRET        = re.compile(r"AKIA[0-9A-Z]{16}")
_RE_SLACK_TOKEN       = re.compile(r"xox[abpr]-[A-Za-z0-9\-]{10,}")
_RE_STRIPE_KEY        = re.compile(r"sk_live_[A-Za-z0-9]{20,}")
_RE_PRIVATE_KEY       = re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
_RE_GENERIC_SECRET    = re.compile(
    r"""(?ix)
    \b(api[_-]?key|secret|password|passwd|token|access[_-]?key)\b
    \s*[:=]\s*
    ['"]([A-Za-z0-9_\-+/=]{16,})['"]
    """,
)
_RE_JWT_LITERAL       = re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")

# CRITICAL – gefährliche Code-Pattern
_RE_PY_BARE_EXCEPT    = re.compile(r"^\s*except\s*:\s*(?:#.*)?$", re.MULTILINE)
_RE_PY_EXCEPT_PASS    = re.compile(r"except\s+[A-Za-z_.]*\s*(?:as\s+\w+)?\s*:\s*\n\s*pass\b")
_RE_JS_EMPTY_CATCH    = re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}")
_RE_PY_EVAL_EXEC      = re.compile(r"(?<![.\w])(eval|exec)\s*\(")
_RE_JS_EVAL           = re.compile(r"(?<![.\w])eval\s*\(")
_RE_REACT_DANGEROUS   = re.compile(r"dangerouslySetInnerHTML")
_RE_INNERHTML_DYNAMIC = re.compile(r"\.innerHTML\s*=\s*[^;'\"]*[+`$]")
_RE_SQL_FSTRING       = re.compile(
    r"""(?ix)
    (execute|query|raw|all|run)\s*\(\s*
    (?:f['"]|['"][^'"]*['"]\s*[+%]\s*\w)
    .*(SELECT|INSERT|UPDATE|DELETE|DROP)
    """,
)

# MAJOR – Qualitäts-Pattern
_RE_JS_CONSOLE_LOG    = re.compile(r"\bconsole\.(log|debug)\s*\(")
_RE_JS_DEBUGGER       = re.compile(r"(?<![.\w])debugger\s*;")
_RE_PY_PRINT          = re.compile(r"^\s*print\s*\(", re.MULTILINE)
_RE_TODO              = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
_RE_TS_ANY            = re.compile(r":\s*any(\b|\[)")
_RE_TS_IGNORE         = re.compile(r"//\s*@ts-(ignore|nocheck|expect-error)")
_RE_TS_AS_UNKNOWN     = re.compile(r"as\s+unknown\s+as\s+")
_RE_NON_NULL_ASSERT   = re.compile(r"[\w\)\]]\!\.")     # foo!.bar
_RE_ALERT_CALL        = re.compile(r"(?<![.\w])alert\s*\(")

# MINOR
_RE_MAGIC_NUMBER      = re.compile(r"(?<![A-Za-z0-9_.])(\d{4,})(?![A-Za-z0-9_.])")  # 1000+, grob


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _should_scan(path: Path, workspace: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix not in _SCAN_EXTENSIONS:
        return False
    try:
        rel_parts = path.relative_to(workspace).parts
    except ValueError:
        return False
    for part in rel_parts:
        if part in _EXCLUDED_DIR_PARTS:
            return False
        if part.endswith(".min.js") or part.endswith(".bundle.js"):
            return False
    return True


def _is_test_file(rel_path: str) -> bool:
    p = rel_path.replace("\\", "/").lower()
    return (
        "/tests/" in p
        or "/test/" in p
        or "/__tests__/" in p
        or p.startswith("tests/")
        or p.startswith("test/")
        or p.endswith("_test.py")
        or p.endswith(".test.ts")
        or p.endswith(".test.tsx")
        or p.endswith(".test.js")
        or p.endswith(".test.jsx")
        or p.endswith(".spec.ts")
        or p.endswith(".spec.tsx")
        or p.endswith(".spec.js")
        or p.endswith(".spec.jsx")
        or p.endswith("_test.go")
    )


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _iter_regex(
    pattern: re.Pattern[str],
    text: str,
    rel_path: str,
    rule: str,
    severity: Severity,
    hint: str = "",
) -> Iterable[Finding]:
    for m in pattern.finditer(text):
        line_no = _line_of(text, m.start())
        snippet_line = text.splitlines()[line_no - 1] if line_no - 1 < len(text.splitlines()) else ""
        yield Finding(
            severity=severity,
            rule=rule,
            path=rel_path,
            line=line_no,
            snippet=snippet_line,
            hint=hint,
        )


# ---------------------------------------------------------------------------
# Datei-Checks
# ---------------------------------------------------------------------------
def _scan_secrets(text: str, rel: str) -> list[Finding]:
    found: list[Finding] = []
    rules = (
        (_RE_OPENAI_KEY,     "secret.openai_key",     "OpenAI-Key im Code – in ENV auslagern."),
        (_RE_ANTHROPIC_KEY,  "secret.anthropic_key",  "Anthropic-Key im Code – in ENV auslagern."),
        (_RE_GITHUB_TOKEN,   "secret.github_token",   "GitHub-Token im Code – in ENV auslagern."),
        (_RE_AWS_SECRET,     "secret.aws_key",        "AWS-Access-Key im Code – in ENV auslagern."),
        (_RE_SLACK_TOKEN,    "secret.slack_token",    "Slack-Token im Code – in ENV auslagern."),
        (_RE_STRIPE_KEY,     "secret.stripe_live",    "Stripe-Live-Key im Code – in ENV auslagern."),
        (_RE_PRIVATE_KEY,    "secret.private_key",    "Privater Schlüssel im Repo – entfernen."),
        (_RE_JWT_LITERAL,    "secret.jwt_literal",    "JWT-Literal – vermutlich echter Token. In ENV/Test-Fixture."),
    )
    for pat, rule, hint in rules:
        found.extend(_iter_regex(pat, text, rel, rule, "critical", hint))
    for m in _RE_GENERIC_SECRET.finditer(text):
        value = m.group(2)
        # Heuristik: offensichtliche Platzhalter ignorieren
        lv = value.lower()
        placeholder_markers = ("changeme", "your_", "xxxx", "placeholder", "example", "replace_me", "dummy", "fake", "secret_here", "todo")
        if any(marker in lv for marker in placeholder_markers):
            continue
        if lv.startswith(("test_", "dummy_", "fake_")):
            continue
        line_no = _line_of(text, m.start())
        snippet_line = text.splitlines()[line_no - 1] if line_no - 1 < len(text.splitlines()) else ""
        found.append(Finding(
            severity="critical",
            rule="secret.hardcoded",
            path=rel,
            line=line_no,
            snippet=snippet_line,
            hint="Hardcoded Secret – via os.environ / process.env laden.",
        ))
    return found


def _scan_python(text: str, rel: str) -> list[Finding]:
    found: list[Finding] = []
    is_test = _is_test_file(rel)

    # CRITICAL
    found.extend(_iter_regex(
        _RE_PY_BARE_EXCEPT, text, rel,
        "py.bare_except", "critical",
        "`except:` verschluckt alles – konkreten Typ angeben.",
    ))
    found.extend(_iter_regex(
        _RE_PY_EXCEPT_PASS, text, rel,
        "py.silent_failure", "critical",
        "Silent failure – mindestens `logger.exception()` und Re-Raise.",
    ))
    found.extend(_iter_regex(
        _RE_PY_EVAL_EXEC, text, rel,
        "py.eval_exec", "critical",
        "eval/exec auf User-Input = Remote-Code-Execution.",
    ))
    found.extend(_iter_regex(
        _RE_SQL_FSTRING, text, rel,
        "sql.string_concat", "critical",
        "SQL-Injection-Risiko – parametrisierte Queries nutzen.",
    ))

    # MAJOR
    if not is_test:
        found.extend(_iter_regex(
            _RE_PY_PRINT, text, rel,
            "py.print_in_prod", "major",
            "`print` durch `logger.info/debug` ersetzen.",
        ))
    found.extend(_iter_regex(
        _RE_TODO, text, rel,
        "note.todo", "major",
        "TODO/FIXME – entweder umsetzen oder mit Ticket-Referenz.",
    ))

    # Funktions-Länge + fehlende Type-Hints (einfacher Parser)
    func_re = re.compile(r"^(\s*)(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*(->\s*[^:]+)?:", re.MULTILINE)
    lines = text.split("\n")
    for m in func_re.finditer(text):
        indent = len(m.group(1))
        name = m.group(2)
        params = m.group(3)
        ret = m.group(4)
        line_no = _line_of(text, m.start())

        # Länge: zähle Folge-Zeilen mit tieferer Einrückung
        end_line = line_no
        for i in range(line_no, len(lines)):
            line_text = lines[i]
            if not line_text.strip() or line_text.startswith((" " * (indent + 1), "\t")):
                end_line = i + 1
            else:
                if i == line_no - 1:
                    continue
                break
        length = end_line - line_no + 1
        if length > 80:
            found.append(Finding(
                severity="major", rule="py.function_too_long", path=rel,
                line=line_no, snippet=f"def {name}(...)  [{length} Zeilen]",
                hint="Funktion > 80 Zeilen – in kleinere Einheiten splitten.",
            ))

        # Public API (nicht _private, nicht test_...) sollte Type-Hints haben
        if not is_test and not name.startswith("_") and not name.startswith("test_"):
            params_clean = params.strip()
            if params_clean and params_clean != "self" and params_clean != "cls":
                # Lose Check: enthält mindestens ein ":" für Annotation
                bare_params = [
                    p.strip() for p in params_clean.split(",")
                    if p.strip() and p.strip() not in {"self", "cls", "*", "/"}
                    and not p.strip().startswith(("*", "**"))
                ]
                untyped = [p for p in bare_params if ":" not in p.split("=")[0]]
                if untyped:
                    found.append(Finding(
                        severity="major", rule="py.missing_type_hints", path=rel,
                        line=line_no, snippet=f"def {name}({params_clean})",
                        hint=f"Parameter ohne Type-Hint: {', '.join(untyped)}",
                    ))
            if ret is None and name not in {"__init__"}:
                found.append(Finding(
                    severity="minor", rule="py.missing_return_type", path=rel,
                    line=line_no, snippet=f"def {name}(...)",
                    hint="Rückgabetyp annotieren (z.B. `-> None`).",
                ))

    return found


def _scan_js_ts(text: str, rel: str) -> list[Finding]:
    found: list[Finding] = []
    is_test = _is_test_file(rel)
    is_ts = rel.endswith((".ts", ".tsx"))

    # CRITICAL
    found.extend(_iter_regex(
        _RE_JS_EMPTY_CATCH, text, rel,
        "js.empty_catch", "critical",
        "Leerer catch-Block – mindestens loggen.",
    ))
    found.extend(_iter_regex(
        _RE_JS_EVAL, text, rel,
        "js.eval", "critical",
        "eval() vermeiden – stattdessen parsen/dispatchen.",
    ))
    found.extend(_iter_regex(
        _RE_REACT_DANGEROUS, text, rel,
        "react.dangerously_set_inner_html", "critical",
        "dangerouslySetInnerHTML – nur mit Sanitizer (DOMPurify).",
    ))
    found.extend(_iter_regex(
        _RE_INNERHTML_DYNAMIC, text, rel,
        "js.innerhtml_dynamic", "critical",
        "Dynamisches innerHTML = XSS-Risiko. textContent / DOM-Nodes nutzen.",
    ))

    # MAJOR
    if not is_test:
        found.extend(_iter_regex(
            _RE_JS_CONSOLE_LOG, text, rel,
            "js.console_log", "major",
            "console.log entfernen oder durch Logger-Abstraktion ersetzen.",
        ))
    found.extend(_iter_regex(
        _RE_JS_DEBUGGER, text, rel,
        "js.debugger", "major",
        "`debugger;` entfernen.",
    ))
    found.extend(_iter_regex(
        _RE_ALERT_CALL, text, rel,
        "js.alert", "major",
        "`alert()` im Prod-Code – durch UI-Notification ersetzen.",
    ))
    found.extend(_iter_regex(
        _RE_TODO, text, rel,
        "note.todo", "major",
        "TODO/FIXME – entweder umsetzen oder mit Ticket-Referenz.",
    ))

    if is_ts:
        found.extend(_iter_regex(
            _RE_TS_ANY, text, rel,
            "ts.any_type", "major",
            "`any` vermeiden – stattdessen `unknown` + Validator oder konkreter Typ.",
        ))
        found.extend(_iter_regex(
            _RE_TS_IGNORE, text, rel,
            "ts.ts_ignore", "major",
            "@ts-ignore/@ts-nocheck/@ts-expect-error – nur mit Begründungs-Kommentar.",
        ))
        found.extend(_iter_regex(
            _RE_TS_AS_UNKNOWN, text, rel,
            "ts.double_cast", "major",
            "`as unknown as X` = Type-System-Umgehung. Lieber Typ korrekt modellieren.",
        ))
        found.extend(_iter_regex(
            _RE_NON_NULL_ASSERT, text, rel,
            "ts.non_null_assertion", "minor",
            "Non-Null-Assertion `!` – prüfen, ob ein Guard sauberer wäre.",
        ))

    # Funktions-Länge (sehr grob)
    func_re = re.compile(
        r"^(?:export\s+)?(?:async\s+)?function\s+\w+\s*\([^)]*\)\s*\{",
        re.MULTILINE,
    )
    lines = text.split("\n")
    for m in func_re.finditer(text):
        line_no = _line_of(text, m.start())
        # Klammer-Tiefe zählen bis 0
        depth = 0
        end = line_no
        for i in range(line_no - 1, len(lines)):
            line_text = lines[i]
            depth += line_text.count("{") - line_text.count("}")
            if depth <= 0 and i > line_no - 1:
                end = i + 1
                break
        length = end - line_no + 1
        if length > 80:
            found.append(Finding(
                severity="major", rule="js.function_too_long", path=rel,
                line=line_no, snippet=lines[line_no - 1],
                hint=f"Funktion {length} Zeilen – in kleinere Einheiten splitten.",
            ))

    return found


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def run_senior_review(workspace_path: Path, file_limit: int = 200) -> ReviewReport:
    """
    Führt den Senior-Review auf dem gesamten Workspace aus.

    `file_limit` begrenzt die Anzahl gescannter Dateien (Default 200), um bei
    riesigen Repos nicht zu blockieren.
    """
    report = ReviewReport()

    candidates: list[Path] = []
    for p in workspace_path.rglob("*"):
        if _should_scan(p, workspace_path):
            candidates.append(p)
            if len(candidates) >= file_limit:
                break

    for path in candidates:
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                report.skipped.append(str(path.relative_to(workspace_path)))
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            report.skipped.append(str(path.relative_to(workspace_path)))
            continue

        rel = str(path.relative_to(workspace_path))
        report.files_reviewed += 1
        report.lines_reviewed += text.count("\n")

        findings: list[Finding] = []
        findings.extend(_scan_secrets(text, rel))
        if path.suffix == ".py":
            findings.extend(_scan_python(text, rel))
        else:
            findings.extend(_scan_js_ts(text, rel))

        # Kappung pro Datei
        if len(findings) > _MAX_FINDINGS_PER_FILE:
            findings = findings[:_MAX_FINDINGS_PER_FILE]

        for f in findings:
            if f.severity == "critical":
                report.critical.append(f)
            elif f.severity == "major":
                report.major.append(f)
            else:
                report.minor.append(f)

    return report
