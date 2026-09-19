---
type: is
id: is-01m2wb8nv8pgy8krq15yh31qy8
title: Pin mcp to 1.x so StructuredContent import works
kind: bug
status: closed
priority: 0
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m2wb8pyw75g2pdfn85aexjyj
parent_id: is-01m2wb8ngskhc23s05wa7tpk9z
created_at: 2026-09-19T08:07:01.735Z
updated_at: 2026-09-19T08:09:27.096Z
closed_at: 2026-09-19T08:09:27.095Z
close_reason: "Fixed in 52023ae: mcp pinned to <2, stale file:// no longer abort identity, prompt/xontrib recover on unexpected exceptions."
resolution: null
duplicate_of: null
---
kash-shell declared mcp>=1.6.0; uv tool install resolved mcp 2.2.0. The v1 low-level Server types are gone. Pin mcp>=1.6.0,<2 and add an import smoke test. Full mcp 2 migration is follow-up.
