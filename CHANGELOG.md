# Changelog

## [0.1.0] - 2026-04-23

### Added
- Initial release.
- CLI `claude-hooks-check` for linting Claude Code hooks configuration (either a full `settings.json` with a `hooks` key, or a standalone hooks JSON).
- Library API: `validate_hooks_file`, `validate_hooks_source`, `validate_settings_file`, `ValidationResult`, `Issue`, `Severity`.
- Checks: unknown event names, matcher-block shape, hook entry `type` and `command`, `timeout` validity, dangerous command patterns (`rm -rf /`, `curl | sh`, `sudo`, `dd` disk wipes, fork bombs), hardcoded secrets in commands (Anthropic/OpenAI/AWS/GitHub/Stripe/Google).
- GitHub Actions CI on Python 3.9-3.13 and a release workflow publishing to PyPI via OIDC trusted publishing.
