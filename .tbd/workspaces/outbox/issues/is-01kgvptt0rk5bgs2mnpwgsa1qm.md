---
created_at: 2026-02-07T09:27:22.903Z
dependencies: []
id: is-01kgvptt0rk5bgs2mnpwgsa1qm
kind: task
labels: []
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Review codebase for python-modern-guidelines conformance
type: is
updated_at: 2026-02-07T18:11:00.995Z
version: 3
---
Review codebase against python-modern-guidelines: (1) from __future__ import annotations on all typed files, (2) @override on all subclass method overrides, (3) atomic_output_file from strif for all file writes, (4) prettyfmt usage for log formatting, (5) modern union syntax X|None not Optional, (6) pathlib Path not strings. Also check python-rules: absolute imports, StrEnum, no if __name__=='__main__' for testing.
