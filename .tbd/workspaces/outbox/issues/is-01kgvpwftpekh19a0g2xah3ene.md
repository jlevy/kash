---
close_reason: Relaxed openai pin from ==1.99.9 to >=1.99,<2.0
closed_at: 2026-02-07T21:40:40.301Z
created_at: 2026-02-07T09:28:18.006Z
dependencies: []
id: is-01kgvpwftpekh19a0g2xah3ene
kind: bug
labels:
  - tier-1-compatible
priority: 2
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: closed
title: Fix openai version pinning (pyproject.toml FIXME)
type: is
updated_at: 2026-02-07T21:40:40.302Z
version: 5
---
Resolve the FIXME at pyproject.toml line 88 regarding `openai==1.99.9` version pinning. The pin exists due to a ResponseTextConfig import error in newer versions. Investigate the root cause: check if the import path changed in a newer openai release, find the correct import, and update to a version range (>=1.99) instead of an exact pin. No API changes—purely a dependency fix.
