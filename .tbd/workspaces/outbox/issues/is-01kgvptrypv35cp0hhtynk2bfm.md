---
created_at: 2026-02-07T09:27:21.814Z
dependencies: []
id: is-01kgvptrypv35cp0hhtynk2bfm
kind: task
labels:
  - tier-1-compatible
priority: 1
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: "Add pure function tests: model, fuzzy_parsing, llm_names, scoring, URL parsing"
type: is
updated_at: 2026-02-07T19:53:48.392Z
version: 4
---
Add pure function tests (no mocks): model (items, params, preconditions, paths), llm_utils (fuzzy_parsing, llm_names), shell (completion_scoring), utils (url, markdown), web_content (canon_url). Follow: general-testing-rules (minimal tests with maximal coverage, no trivial tests, test edge cases), python-rules (testing: no pytest fixtures unless complex, no assert messages, no assert False), general-tdd-guidelines (unit tests: fast, focused, no network).
