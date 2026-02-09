---
close_reason: Extracted 15+ magic numbers in completion_scoring.py to named constants with docstrings
closed_at: 2026-02-07T21:42:51.899Z
created_at: 2026-02-07T09:28:17.595Z
dependencies: []
id: is-01kgvpwfdwa43b0vvb6n2bqx6g
kind: task
labels:
  - tier-1-compatible
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: closed
title: Extract named constants from magic numbers (scoring, ports, timing)
type: is
updated_at: 2026-02-09T05:32:59.051Z
version: 11
---
Extract named constants from magic numbers per general-coding-rules: 'NEVER hardcode numeric values directly. All numeric constants must have clear, descriptive names and docstrings.' Known locations: completion_scoring.py (scoring weights, thresholds), settings.py (port range 4470-4499), web_fetch.py (30s timeout), various buffer sizes.
