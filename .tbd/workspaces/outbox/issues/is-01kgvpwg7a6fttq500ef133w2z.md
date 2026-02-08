---
created_at: 2026-02-07T09:28:18.409Z
dependencies: []
id: is-01kgvpwg7a6fttq500ef133w2z
kind: feature
labels:
  - tier-2-additive
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Create standalone CLI for individual kash actions
type: is
updated_at: 2026-02-08T18:06:10.859Z
version: 8
---
Create standalone CLI for individual kash actions per python-cli-patterns. Use Typer or argparse+rich_argparse. Support --format text|json, --non-interactive, --no-progress, --dry-run. Exit codes: 0=success, 1=error, 2=validation, 130=SIGINT. Enable running 'kash run <action> --input ...' without xonsh.
