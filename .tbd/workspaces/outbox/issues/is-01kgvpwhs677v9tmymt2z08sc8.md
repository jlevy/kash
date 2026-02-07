---
created_at: 2026-02-07T09:28:20.006Z
dependencies: []
id: is-01kgvpwhs677v9tmymt2z08sc8
kind: task
labels:
  - tier-3-breaking
priority: 3
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Audit and reorganize utils/ directory (72 files across 7 subdirs)
type: is
updated_at: 2026-02-07T19:53:48.550Z
version: 4
---
Audit and reorganize utils/ directory (72 files across 7 subdirs). TIER 3 BREAKING: if any symbols move, kash-docs (uses Url, MarkdownFootnotes, gather_limited, etc in 74 import statements) and kash-media (uses Url, errors, format_utils, etc) must update imports. Requires coordinated release.
