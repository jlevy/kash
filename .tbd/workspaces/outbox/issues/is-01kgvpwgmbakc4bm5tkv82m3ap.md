---
created_at: 2026-02-07T09:28:18.826Z
dependencies: []
id: is-01kgvpwgmbakc4bm5tkv82m3ap
kind: feature
labels: []
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Add --format json and --non-interactive flags for agent/CI use
type: is
updated_at: 2026-02-07T18:11:01.121Z
version: 3
---
Add --format json and --non-interactive flags per python-cli-patterns. Implement OutputManager for dual text/JSON output. Route data to stdout, errors/warnings to stderr. Disable spinners/progress in non-TTY contexts. Respect CI and NO_COLOR env vars.
