---
created_at: 2026-02-07T09:27:22.549Z
dependencies: []
id: is-01kgvptsnn2jv8gxsjmyweqjg3
kind: task
labels: []
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: "Add integration tests: action_exec pipeline, web_fetch, MCP routes"
type: is
updated_at: 2026-02-07T18:11:00.985Z
version: 3
---
Add integration tests: action_exec pipeline (mocked ws+LLM), web_fetch (mock httpx), local_file_cache, MCP routes, workspace commands. Follow: general-tdd-guidelines (integration tests), golden-testing-guidelines (consider golden session tests for action pipelines—capture input/output Items as YAML, filter unstable fields like timestamps). File naming: test_*_integration.py.
