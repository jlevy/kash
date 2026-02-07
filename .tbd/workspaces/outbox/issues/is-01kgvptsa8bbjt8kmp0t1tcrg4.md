---
created_at: 2026-02-07T09:27:22.184Z
dependencies:
  - target: is-01kgvptsnn2jv8gxsjmyweqjg3
    type: blocks
id: is-01kgvptsa8bbjt8kmp0t1tcrg4
kind: task
labels: []
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: "Add mocked tests: action_registry, resolve_args, selections, llm_completion"
type: is
updated_at: 2026-02-07T18:11:00.976Z
version: 4
---
Add mocked dependency tests: action_registry, resolve_args, precondition_checks, selections, param_state, item_id_index, llm_completion, sliding_transforms. Follow: general-testing-rules (behavior not implementation, edge cases), general-tdd-guidelines (integration tests: mock external APIs, no network), python-rules (testing patterns).
