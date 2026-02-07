---
created_at: 2026-02-07T09:28:15.898Z
dependencies:
  - target: is-01kgvptsa8bbjt8kmp0t1tcrg4
    type: blocks
  - target: is-01kgvptrypv35cp0hhtynk2bfm
    type: blocks
id: is-01kgvpwdrvhnhgzd8amv7cp6ka
kind: task
labels:
  - tier-1-compatible
priority: 1
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: "Create test infrastructure: conftest.py, fixtures, test factories"
type: is
updated_at: 2026-02-07T19:53:48.477Z
version: 6
---
Create tests/conftest.py with shared fixtures (temp_workspace, mock_current_ws, mock_llm, sample_item). Add pytest markers (@pytest.mark.slow, @pytest.mark.online, @pytest.mark.golden). Follow: general-testing-rules (minimal tests, maximal coverage), python-rules (testing section: inline tests for simple cases, tests/ for longer), general-tdd-guidelines (unit/integration/golden/E2E categories).
