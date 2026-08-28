# Repository Agent Contract

## Mission

Safely evolve Tender Document Checker while preserving its existing behavior, integrations, and development toolchain.

## Repository Map

- `main.py`, `streamlit_ui.py`: primary runtime entry points/UI surfaces.
- `src/`: typed configuration, models, logging, and selected integrations.
- root `*.py`: existing application, analysis, audit, workflow, pricing, notification, and integration modules.
- `tests/`: primary pytest suite.
- `data/`: internal standards, tolerances, sample/report data.
- `prompts/`: LLM prompt assets.
- `.github/workflows/ci.yml`: authoritative CI pipeline.
- `pyproject.toml`: Python, dependency, Ruff, mypy, pytest, and coverage configuration.

## Build / Install

```bash
uv sync --extra dev
```

## Quality Commands

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest tests/ -v
```

`make lint`, `make format`, and `make test` may also be used where they match the task.

## Engineering Rules

1. Research existing implementation, tests, configuration, and conventions before editing.
2. Prefer reuse -> extend -> compose -> create new.
3. Keep the change bounded; do not mix environment setup with application refactoring.
4. Do not move root modules into `src/` (or the reverse) unless a dedicated architecture change authorizes it.
5. Preserve external integration contracts unless the requirement explicitly changes them.
6. New or modified external side effects must have an observable error path and appropriate audit/logging.
7. Do not introduce secrets or real external credentials.
8. Business-critical external writes require human review before merge.

## Testing Contract

- Fix: failing reproduction -> implementation -> passing regression test.
- Feature: acceptance behavior -> cheapest proving test -> integration/E2E only when needed.
- AI-generated tests are production code and must prove behavior rather than merely mirror the implementation.

## Agent Roles

- Architect: inspect and plan; do not make broad edits.
- Implementer: implement only the approved bounded plan and add/update tests.
- Reviewer: review the diff for correctness, regression, architecture, security, typing, tests, observability, and external side effects; do not silently rewrite the implementation.

## Stop Conditions

Stop and request a decision when the task requires a breaking API change, destructive data migration, security/permission boundary change, production credentials, ambiguous business rules, cross-domain redesign, or unexpectedly large diff.

## Definition of Done

- Acceptance criteria are met.
- Scope is minimal and existing architecture/tooling is preserved.
- Ruff, mypy, and relevant pytest checks pass, or unavailable checks are explicitly marked NOT EXECUTED with reason.
- No secrets or accidental external writes are introduced.
- Documentation is updated only when behavior/contract/workflow changed.
- PR contains scope, tests/evidence, risks, and rollback notes.
