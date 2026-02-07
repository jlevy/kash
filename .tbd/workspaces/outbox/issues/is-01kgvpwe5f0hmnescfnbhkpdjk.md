---
created_at: 2026-02-07T09:28:16.302Z
dependencies:
  - target: is-01kgvpwgmbakc4bm5tkv82m3ap
    type: blocks
id: is-01kgvpwe5f0hmnescfnbhkpdjk
kind: feature
labels:
  - tier-2-additive
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Design and implement ShellContext protocol for shell decoupling
type: is
updated_at: 2026-02-07T19:53:48.484Z
version: 4
---
Design and implement a ShellContext protocol to decouple command execution from xonsh. Define Protocol with methods: set_env(), print_output(), get_workspace(), record_history(). Create implementations: XonshShellContext (wraps current xonsh env), StandaloneContext (for library/script use), CLIContext (for standalone CLI commands). BACKWARD COMPAT: existing shell code continues to work via XonshShellContext—this is a new abstraction layer, not a replacement. Blocks kash-5ew2 (--format json flags).
