---
created_at: 2026-02-07T09:28:18.006Z
dependencies: []
id: is-01kgvpwftpekh19a0g2xah3ene
kind: bug
labels:
  - tier-1-compatible
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Fix openai version pinning (pyproject.toml FIXME)
type: is
updated_at: 2026-02-07T19:53:48.512Z
version: 3
---
Resolve the FIXME at pyproject.toml line 88 regarding `openai==1.99.9` version pinning. The pin exists due to a ResponseTextConfig import error in newer versions. Investigate the root cause: check if the import path changed in a newer openai release, find the correct import, and update to a version range (>=1.99) instead of an exact pin. No API changes—purely a dependency fix.
