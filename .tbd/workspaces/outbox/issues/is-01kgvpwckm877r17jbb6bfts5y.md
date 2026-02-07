---
created_at: 2026-02-07T09:28:14.707Z
dependencies:
  - target: is-01kgvpwd06s2vdjn332q4447gk
    type: blocks
  - target: is-01kgvpwjwxg1h8c6b4fk5xhnpc
    type: blocks
id: is-01kgvpwckm877r17jbb6bfts5y
kind: task
labels:
  - tier-2-additive
priority: 1
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Eliminate import side effects - make action/command registration lazy
type: is
updated_at: 2026-02-07T19:53:48.452Z
version: 6
---
Eliminate import side effects - make action/command registration lazy. BACKWARD COMPAT: must ensure 'import kash.actions' and 'import kash.commands' still triggers registration (via __getattr__ or equivalent). import_and_register() used by kash-docs and kash-media must work identically. kash_setup() -> kash_reload_all() initialization order must be preserved.
