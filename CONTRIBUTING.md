# Contributing to Azure Speech-to-Text for Home Assistant

Thank you for considering contributing to this project. This guide covers the development setup, testing, and submission process.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- A Home Assistant instance (for integration testing)

## Development Setup

```bash
git clone https://github.com/hass-cortex/azure-speech-stt.git
cd azure-speech-stt
uv sync --group dev --group test
```

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=custom_components --cov-report=term-missing

# Run a specific test file
uv run pytest tests/test_stt_corrector.py -v
```

## Code Style

This project enforces consistent code style via automated tooling:

- **Linting**: `uv run ruff check .`
- **Formatting**: `uv run ruff format .`
- **Type checking**: `uv run mypy custom_components/`
- Follow Google-style docstrings for all public functions and classes

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use case |
|--------|----------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `chore:` | Maintenance / tooling |
| `refactor:` | Code restructure without behavior change |
| `test:` | Adding or updating tests |

Example: `feat: add support for custom phonetic matchers`

## Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes with appropriate tests
4. Ensure all checks pass (`ruff check`, `ruff format --check`, `pytest`)
5. Submit a pull request with a clear description of the change

## Project Structure

```
azure-speech-stt/
  custom_components/azure_speech_stt/
    __init__.py          # Integration setup (credential validation, platform forwarding)
    stt.py               # STT entity (audio processing, correction, statistics)
    sensor.py            # Runtime statistics sensors (12 sensors, RestoreSensor)
    models.py            # Runtime data models (AzureSTTRuntimeData)
    azure_client.py      # Azure API client (Fast Transcription + Real-time)
    config_flow.py       # Config, options, reauth flows
    correction_config.py # Correction config dataclass
    helpers.py           # Entity lookup helpers
    phrase_builder.py    # HA registry phrase collection
    services.py          # Service handlers
    const.py             # Constants, locales, regions
    stt_corrector/       # Correction pipeline (fuzzy, pinyin, custom rules)
  tests/                 # Test suite
  docs/                  # Documentation
  pyproject.toml         # Project metadata and tool config
```

## Reporting Issues

Please use GitHub Issues with the provided templates. Include:

- Home Assistant version
- Integration version
- Steps to reproduce
- Expected vs actual behavior
- Relevant debug logs (see README for how to enable debug logging)
