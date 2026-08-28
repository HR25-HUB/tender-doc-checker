---
applyTo: "**/*.py"
---

# Python Instructions

- Target Python 3.11+ and preserve compatibility with the versions exercised by CI.
- Use the repository's existing uv/Ruff/mypy/pytest toolchain. Do not introduce a second formatter, linter, type checker, or test framework.
- Add explicit type annotations to new/changed production code where practical and keep it compatible with the existing mypy configuration.
- Use Pydantic v2 models/settings for typed external data, API DTOs, configuration, or AI structured outputs when a typed boundary is needed.
- Reuse existing models/configuration before introducing duplicate schemas.
- Keep deterministic business rules testable without network calls.
- External calls (Bitrix24, email, ERP, OpenAI) must have explicit error handling; tests should mock writes unless the Issue explicitly requests an integration test.
- Do not use blanket exception swallowing, global lint suppression, or unjustified type ignores.
- For changed code, run the narrowest relevant tests first, then the repository quality gates before PR.
