---
close_reason: Removed 5 unused deps (tenacity, tiktoken, selectolax, pluralizer, rich-argparse). Added optional dependency groups [llm], [web], [media], [server], [shell], [all]. All 174 tests pass.
closed_at: 2026-02-08T04:55:55.144Z
created_at: 2026-02-07T09:28:15.506Z
dependencies: []
id: is-01kgvpwdck99j45ma9d93xj8th
kind: task
labels:
  - tier-2-additive
priority: 1
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: closed
title: Remove unused dependencies and create optional dependency groups
type: is
updated_at: 2026-02-08T16:58:13.661Z
version: 8
---
Remove unused dependencies and create optional dependency groups. BACKWARD COMPAT: only remove deps confirmed unused by kash AND downstream (kash-docs, kash-media). Keep current deps in default install. Add optional groups [llm], [media], [web], [server], [shell] for new users who want minimal installs.
