---
created_at: 2026-02-07T09:27:23.259Z
dependencies: []
id: is-01kgvpttbwe9xmg59bf4w1q6mz
kind: task
labels: []
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Review codebase for error-handling-rules conformance
type: is
updated_at: 2026-02-07T18:11:01.004Z
version: 3
---
Review codebase against error-handling-rules: (1) Error handling as feature—audit happy-path-only functions, (2) No debug-only error handling (Anti-Pattern 1), (3) Exit codes as API contracts (currently only 0/1), (4) Transient vs permanent error classification for retry logic, (5) Tests must verify error behavior, (6) Logging is not handling—find log-without-control-flow-change patterns, (7) Consider custom exception hierarchy (CLIError, ValidationError, TransientError).
