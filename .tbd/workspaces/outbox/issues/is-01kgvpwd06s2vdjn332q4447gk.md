---
close_reason: Implemented kash.run module with kash_init() and kash_run() functions. No xonsh dependency needed. 13 tests pass. Exports added to root kash package.
closed_at: 2026-02-08T05:07:16.847Z
created_at: 2026-02-07T09:28:15.109Z
dependencies:
  - target: is-01kgvpwg7a6fttq500ef133w2z
    type: blocks
  - target: is-01kgvpwe5f0hmnescfnbhkpdjk
    type: blocks
  - target: is-01kgvpwh1f7vra1hbtq9gw7vs7
    type: blocks
id: is-01kgvpwd06s2vdjn332q4447gk
kind: feature
labels:
  - tier-2-additive
priority: 1
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: closed
title: Create standalone action runner (kash.run()) for library use
type: is
updated_at: 2026-02-08T17:49:56.640Z
version: 11
---
Create a standalone action runner function `kash.run()` that can execute any kash action without the shell. Must work with explicit `kash.init()` initialization, no xonsh dependency. Return structured `ActionResult` with items, not console output. Minimal required configuration. BACKWARD COMPAT: does not change existing action execution—this is a new function alongside the existing pipeline. Depends on clean public API (kash-ymq4) and lazy imports (kash-y80s). Per python-cli-patterns: support structured return types for programmatic use.
