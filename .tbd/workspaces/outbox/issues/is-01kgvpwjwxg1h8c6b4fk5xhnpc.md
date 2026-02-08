---
created_at: 2026-02-07T09:28:21.148Z
dependencies: []
id: is-01kgvpwjwxg1h8c6b4fk5xhnpc
kind: feature
labels:
  - tier-3-breaking
priority: 3
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Implement lightweight MCP mode for selective action loading
type: is
updated_at: 2026-02-08T18:06:10.908Z
version: 7
---
Implement a lightweight MCP mode that only loads requested actions instead of the full registry. Currently the MCP server requires full kash initialization including all registries, workspace system, and configuration. Goal: expose a single action as an MCP tool without loading everything. Also consider: direct Claude Code skill integration (wrap key actions as skills without running MCP server), skill template generation from @kash_action metadata. TIER 3 BREAKING: may change how action discovery works internally. Depends on lazy import elimination (kash-y80s).
