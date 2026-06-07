"""Command-line entry point for claude-hooks-check."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from claude_hooks_check import __version__
from claude_hooks_check.validator import Severity, ValidationResult, validate_hooks_file


def _format_human(results: list[ValidationResult]) -> str:
    lines: list[str] = []
    total_errors = 0
    total_warnings = 0
    for r in results:
        if not r.issues:
            lines.append(f"OK  {r.path}")
            continue
        lines.append(f"{r.path}:")
        for i in r.issues:
            where_parts = []
            if i.event:
                where_parts.append(i.event)
            if i.matcher:
                where_parts.append(i.matcher)
            where = f" [{'/'.join(where_parts)}]" if where_parts else ""
            lines.append(f"  {i.severity.value:7s} {i.code}{where} {i.message}")
            if i.severity is Severity.ERROR:
                total_errors += 1
            else:
                total_warnings += 1
    lines.append("")
    lines.append(
        f"{len(results)} file(s), {total_errors} error(s), {total_warnings} warning(s)"
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="claude-hooks-check",
        description="Lint Claude Code hooks configuration.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Hooks JSON file paths (or a settings.json containing a 'hooks' key)",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Only print errors")
    parser.add_argument(
        "--version",
        action="version",
        version=f"claude-hooks-check {__version__}",
    )
    args = parser.parse_args(argv)

    results = [validate_hooks_file(Path(p)) for p in args.paths]

    if args.quiet:
        filtered = [
            ValidationResult(path=r.path, issues=list(r.errors))
            for r in results
            if r.errors
        ]
        if filtered:
            print(_format_human(filtered))
    else:
        print(_format_human(results))

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
