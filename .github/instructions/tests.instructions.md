---
applyTo: "tests/**/*.py,test_*.py"
---

# Test Instructions

- Tests must validate observable behavior and failure modes, not simply restate implementation details.
- For a bug fix, add or identify a test that fails before the fix when practical.
- Mock external network/write boundaries such as Bitrix24, SMTP, ERP, and OpenAI unless the test is explicitly integration-scoped.
- Prefer deterministic fixtures and avoid reliance on live credentials or mutable production data.
- Do not weaken existing assertions, remove tests, or suppress warnings merely to obtain a green run.
- Keep test data free of real customer PII and secrets.
