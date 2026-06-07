"""Core validation logic for Claude Code hooks configuration.

A valid ``hooks`` block is a JSON object whose keys are event names
(for example ``PreToolUse``, ``PostToolUse``, ``UserPromptSubmit``,
``Stop``, ``Notification``, ``SubagentStop``, ``PreCompact``, ``SessionStart``).
Each value is a list of matcher objects:

    {
      "PreToolUse": [
        {
          "matcher": "Bash",
          "hooks": [
            { "type": "command", "command": "echo hi", "timeout": 60 }
          ]
        }
      ]
    }

This validator accepts either a standalone hooks JSON (``{"hooks": {...}}``
or just ``{...}``) or a full Claude Code ``settings.json`` (it will
extract the ``hooks`` key).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

KNOWN_EVENTS = frozenset(
    {
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "Notification",
        "Stop",
        "SubagentStop",
        "PreCompact",
        "SessionStart",
        "SessionEnd",
    }
)

ACCEPTED_HOOK_TYPES = frozenset({"command"})

DANGEROUS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("rm -rf /", re.compile(r"\brm\s+-[rR]?f?[rR]?\s+/\s*($|[^/\w])")),
    ("curl | sh piping", re.compile(r"curl\s[^|]*\|\s*(sh|bash|zsh|python)\b")),
    ("wget | sh piping", re.compile(r"wget\s[^|]*\|\s*(sh|bash|zsh|python)\b")),
    ("sudo command", re.compile(r"(^|\s)sudo\b")),
    ("disk wipe (dd)", re.compile(r"\bdd\s+if=[^\s]+\s+of=/dev/")),
    ("fork bomb", re.compile(r":\(\)\s*\{\s*:\|:&\s*\};?:")),
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("Stripe live key", re.compile(r"sk_live_[A-Za-z0-9]{24,}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    message: str
    event: str | None = None
    matcher: str | None = None


@dataclass
class ValidationResult:
    path: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity is Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]


def _err(
    code: str, msg: str, event: str | None = None, matcher: str | None = None
) -> Issue:
    return Issue(Severity.ERROR, code, msg, event, matcher)


def _warn(
    code: str, msg: str, event: str | None = None, matcher: str | None = None
) -> Issue:
    return Issue(Severity.WARNING, code, msg, event, matcher)


def _check_command(cmd: str, event: str, matcher: str) -> list[Issue]:
    out: list[Issue] = []
    for label, pat in DANGEROUS_PATTERNS:
        if pat.search(cmd):
            out.append(
                _err(
                    "E200",
                    f"dangerous command pattern detected: {label}",
                    event,
                    matcher,
                )
            )
    for label, pat in SECRET_PATTERNS:
        if pat.search(cmd):
            out.append(
                _err(
                    "E201",
                    f"possible {label} hardcoded in hook command",
                    event,
                    matcher,
                )
            )
    return out


def _check_hook_entry(hook: Any, event: str, matcher: str) -> list[Issue]:
    if not isinstance(hook, dict):
        return [_err("E101", "hook entry must be an object", event, matcher)]
    issues: list[Issue] = []

    htype = hook.get("type")
    if htype is None:
        issues.append(_err("E102", "hook entry missing 'type'", event, matcher))
    elif htype not in ACCEPTED_HOOK_TYPES:
        issues.append(
            _err(
                "E103",
                f"unknown hook type '{htype}' (expected one of: {sorted(ACCEPTED_HOOK_TYPES)})",
                event,
                matcher,
            )
        )

    if htype == "command":
        cmd = hook.get("command")
        if not isinstance(cmd, str) or not cmd.strip():
            issues.append(
                _err(
                    "E104",
                    "'command' must be a non-empty string for a command hook",
                    event,
                    matcher,
                )
            )
        else:
            issues.extend(_check_command(cmd, event, matcher))

    if "timeout" in hook:
        t = hook["timeout"]
        if not (isinstance(t, int) and not isinstance(t, bool) and t > 0):
            issues.append(
                _err(
                    "E105",
                    "'timeout' must be a positive integer (seconds)",
                    event,
                    matcher,
                )
            )
        elif t > 3600:
            issues.append(
                _warn(
                    "W105",
                    f"'timeout' is {t}s (>1h); most hooks should finish in seconds",
                    event,
                    matcher,
                )
            )

    return issues


def _check_matcher_block(mb: Any, event: str) -> list[Issue]:
    if not isinstance(mb, dict):
        return [_err("E050", "matcher block must be an object", event)]
    issues: list[Issue] = []

    matcher = mb.get("matcher")
    if matcher is not None and not isinstance(matcher, str):
        issues.append(_err("E051", "'matcher' must be a string (or omitted)", event))
    matcher_label = matcher if isinstance(matcher, str) and matcher else "*"

    hooks = mb.get("hooks")
    if hooks is None:
        issues.append(
            _err("E052", "matcher block missing 'hooks' array", event, matcher_label)
        )
        return issues
    if not isinstance(hooks, list):
        issues.append(_err("E053", "'hooks' must be an array", event, matcher_label))
        return issues
    if not hooks:
        issues.append(
            _warn(
                "W054", "matcher block has an empty 'hooks' array", event, matcher_label
            )
        )

    for h in hooks:
        issues.extend(_check_hook_entry(h, event, matcher_label))

    return issues


def _check_hooks_block(hooks: Any) -> list[Issue]:
    if not isinstance(hooks, dict):
        return [_err("E010", f"'hooks' must be an object, got {type(hooks).__name__}")]
    issues: list[Issue] = []

    if not hooks:
        issues.append(_warn("W011", "'hooks' object is empty"))
        return issues

    for event, value in hooks.items():
        if event not in KNOWN_EVENTS:
            issues.append(_warn("W020", f"unknown event name '{event}'"))
        if not isinstance(value, list):
            issues.append(
                _err(
                    "E021",
                    f"event '{event}' must map to an array of matcher blocks",
                    event,
                )
            )
            continue
        if not value:
            issues.append(
                _warn("W022", f"event '{event}' has no matcher blocks", event)
            )
            continue
        for mb in value:
            issues.extend(_check_matcher_block(mb, event))

    return issues


def validate_hooks_source(source: str, path: str = "<string>") -> ValidationResult:
    """Validate a standalone hooks JSON or the 'hooks' block of a settings.json."""
    result = ValidationResult(path=path)

    if not source.strip():
        result.issues.append(_err("E000", "file is empty"))
        return result

    try:
        data = json.loads(source)
    except json.JSONDecodeError as exc:
        result.issues.append(_err("E000", f"invalid JSON: {exc}"))
        return result

    if not isinstance(data, dict):
        result.issues.append(
            _err("E000", f"root must be a JSON object, got {type(data).__name__}")
        )
        return result

    # Accept either { "hooks": {...}, "permissions": {...}, ... }
    # or a bare {...} assumed to be the hooks block itself.
    if "hooks" in data and isinstance(data["hooks"], dict):
        hooks = data["hooks"]
    elif set(data.keys()) & KNOWN_EVENTS:
        hooks = data
    elif "hooks" in data:
        result.issues.append(_err("E010", "'hooks' must be an object"))
        return result
    else:
        result.issues.append(
            _warn(
                "W001",
                "no 'hooks' key and no recognized event name at the root; nothing to lint",
            )
        )
        return result

    result.issues.extend(_check_hooks_block(hooks))
    return result


def validate_hooks_file(path: str | Path) -> ValidationResult:
    p = Path(path)
    if not p.exists():
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"file not found: {p}"))
        return r
    if not p.is_file():
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"not a regular file: {p}"))
        return r
    try:
        source = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"file is not valid UTF-8: {exc}"))
        return r
    return validate_hooks_source(source, path=str(p))


# Alias: validate a full Claude Code settings.json (looks at its .hooks key).
def validate_settings_file(path: str | Path) -> ValidationResult:
    return validate_hooks_file(path)
