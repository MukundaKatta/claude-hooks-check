"""claude-hooks-check: linter for Claude Code hooks configuration."""

from claude_hooks_check.validator import (
    Issue,
    Severity,
    ValidationResult,
    validate_hooks_file,
    validate_hooks_source,
    validate_settings_file,
)

__all__ = [
    "Issue",
    "Severity",
    "ValidationResult",
    "validate_hooks_file",
    "validate_hooks_source",
    "validate_settings_file",
]

__version__ = "0.1.0"
