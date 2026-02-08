---
close_reason: "Added 36 integration tests across 4 test files: action_exec pipeline (7), web_fetch (8), local_file_cache (9), kash.run (13). Total project: 210 tests passing."
closed_at: 2026-02-08T05:13:38.123Z
created_at: 2026-02-07T09:27:22.549Z
dependencies: []
id: is-01kgvptsnn2jv8gxsjmyweqjg3
kind: task
labels:
  - tier-1-compatible
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: closed
title: "Add integration tests: action_exec pipeline, web_fetch, MCP routes"
type: is
updated_at: 2026-02-08T05:14:24.515Z
version: 7
---
Add integration tests: action_exec pipeline (mocked ws+LLM), web_fetch (mock httpx), local_file_cache, MCP routes, workspace commands. Follow: general-tdd-guidelines (integration tests), golden-testing-guidelines (consider golden session tests for action pipelines—capture input/output Items as YAML, filter unstable fields like timestamps). File naming: test_*_integration.py.
