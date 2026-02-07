---
created_at: 2026-02-07T09:28:14.280Z
dependencies:
  - target: is-01kgvpwd06s2vdjn332q4447gk
    type: blocks
id: is-01kgvpwc68q9h7r89vb5ssqyvq
kind: task
labels:
  - tier-2-additive
priority: 1
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Define clean public API surface in __init__.py files
type: is
updated_at: 2026-02-07T19:53:48.444Z
version: 5
---
Define clean public API surface: add __all__ to all public modules, add canonical imports to root __init__.py. BACKWARD COMPAT: all existing import paths must remain valid. This is purely additive—new canonical paths, old paths still work. Apply python-rules and python-modern-guidelines.
