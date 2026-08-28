# GitHub Copilot Repository Instructions

## Mission

This repository implements an AI-assisted tender document checker for wholesale/distribution workflows. It analyzes tender documents, applies internal standards, exposes FastAPI and Streamlit interfaces, and integrates with systems such as Bitrix24, email, ERP sources, and SQLite audit/history storage.

## Existing Toolchain

Preserve the repository's native toolchain unless a separate migration issue explicitly changes it:

- Python 3.11+
- uv for dependency and environment management
- Ruff for formatting and linting
- mypy for static typing
- pytest for tests
- Pydantic v2 / pydantic-settings for typed configuration and contracts
- FastAPI for API endpoints
- Streamlit for the analyst UI

Use the same commands as CI:

```bash
uv sync --extra dev
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest tests/ -v
```

## Repository Boundaries

- The repository currently contains both root-level application modules and a `src/` package. Do not relocate modules or perform broad package restructuring as part of unrelated work.
- Reuse existing modules, configuration, models, tests, and integrations before creating new abstractions.
- Preserve existing public API behavior unless the Issue explicitly authorizes a breaking change.
- Treat `data/internal_standards.yaml` and related configuration as business-rule inputs, not hard-coded constants to duplicate in Python.

## Coding Rules

- Use explicit type hints for changed/new production Python code.
- Use Pydantic models for external/API/AI structured boundaries where appropriate.
- Keep pure decision logic separable from external side effects when modifying integration-heavy flows.
- Do not hide errors with broad `except Exception` unless the boundary requires it and the failure is logged/re-raised or converted to an explicit domain result.
- Do not add dependencies when the standard library or an existing dependency solves the problem adequately.
- Never commit credentials, tokens, private certificates, customer PII, or production secrets. Use `.env.example` and environment variables.

## High-Risk Actions

Changes that can send email, mutate Bitrix24/ERP state, alter pricing decisions, change permissions/authentication, or affect external customers require explicit scope, deterministic validation, and human review before merge. Tests should mock external writes unless an integration test is explicitly authorized.

## Testing

For bug fixes: reproduce the defect with a failing test first when practical, then implement the fix. Prefer behavior-focused tests over implementation-detail mocks. Add boundary/error-path tests for changed integration logic.

## Git / PR Rules

- Work on a branch; never implement directly on `main`.
- Keep changes bounded to the Issue.
- Do not disable tests, silence lint/type rules globally, or delete failing tests to make CI green.
- Before PR, run the available deterministic checks and report actual PASS/FAIL/NOT EXECUTED evidence.
- Human approval remains required for business-critical changes.
