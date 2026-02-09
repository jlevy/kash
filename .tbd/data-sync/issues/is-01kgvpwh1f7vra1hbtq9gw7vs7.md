---
created_at: 2026-02-07T09:28:19.246Z
dependencies: []
id: is-01kgvpwh1f7vra1hbtq9gw7vs7
kind: feature
labels:
  - tier-2-additive
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Create KashTestRunner for testing loop integration
type: is
updated_at: 2026-02-09T05:32:59.077Z
version: 8
---
Create KashTestRunner for testing loop integration. Target: developers running kash in automated test/eval loops. Must support: no console output during test runs, deterministic behavior (mock LLM calls), easy workspace setup/teardown via tmp_path, assert-friendly return types. Enable running action pipelines in pytest with mocked dependencies. Per general-tdd-guidelines and general-testing-rules: support unit and integration test patterns.
