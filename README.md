# claude-hooks-check

[![CI](https://github.com/MukundaKatta/claude-hooks-check/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/claude-hooks-check/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/claude-hooks-check.svg)](https://pypi.org/project/claude-hooks-check/)
[![Python](https://img.shields.io/pypi/pyversions/claude-hooks-check.svg)](https://pypi.org/project/claude-hooks-check/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A small Python linter for [Claude Code](https://claude.ai/code) **hooks configuration** — the `hooks` block inside your `settings.json`, or a standalone hooks JSON.

It catches the common foot-guns before you hand a command to Claude that it will silently run on your machine:

- unknown event names (typos like `PreToolYse`, `SessionStrat`)
- malformed matcher blocks (missing `hooks` array, wrong shape)
- hook entries missing `type` or with an unknown type
- command hooks with empty / non-string `command`
- **dangerous command patterns**: `rm -rf /`, `curl | sh`, `sudo ...`, `dd if=... of=/dev/...`, fork bombs
- **hardcoded secrets** in command strings (Anthropic, OpenAI, AWS, GitHub, Stripe, Google)
- invalid or suspiciously-high `timeout` values

Accepts both shapes:

- a full Claude Code `settings.json` — the linter reads its `hooks` key
- a bare hooks JSON — e.g. `{ "PreToolUse": [...] }`

## Install

```bash
pip install claude-hooks-check
```

## Usage

```bash
claude-hooks-check ~/.claude/settings.json
claude-hooks-check .claude/settings.json
```

Exit status: `0` on no errors, `1` on any errors.

## Library API

```python
from claude_hooks_check import validate_hooks_file

result = validate_hooks_file(".claude/settings.json")
for issue in result.errors:
    print(issue.code, issue.event, issue.matcher, issue.message)
```

## Issue codes

| Code | Severity | Meaning |
|------|----------|---------|
| E000 | error | file-level problem (missing, empty, not JSON, not an object) |
| E010 | error | `hooks` is not an object |
| E021 | error | event value is not an array |
| E050 | error | matcher block is not an object |
| E051 | error | `matcher` is not a string |
| E052 | error | matcher block missing `hooks` array |
| E053 | error | `hooks` is not an array |
| E101 | error | hook entry is not an object |
| E102 | error | hook entry missing `type` |
| E103 | error | unknown hook `type` |
| E104 | error | command hook has empty / non-string `command` |
| E105 | error | `timeout` is not a positive integer |
| E200 | error | dangerous command pattern detected |
| E201 | error | hardcoded secret in command |
| W001 | warning | no `hooks` and no recognized event at root |
| W011 | warning | `hooks` object is empty |
| W020 | warning | unknown event name |
| W022 | warning | event has no matcher blocks |
| W054 | warning | matcher block has empty `hooks` array |
| W105 | warning | `timeout` over one hour |

## Use as a GitHub Action

Add this step to any workflow:

```yaml
- uses: actions/checkout@v5
- uses: MukundaKatta/claude-hooks-check@v1
  with:
    paths: .claude/settings.json
```

Pass multiple files space-separated (e.g. `paths: .claude/settings.json .claude/settings.local.json`). The action runs the same checks as the CLI and fails the workflow on any errors. Inputs: `paths` (required), `quiet` (default `false`), `python-version` (default `3.12`).

## License

MIT