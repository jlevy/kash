---
type: is
id: is-01m2wb8p7hre92tc86j6fdaj0a
title: Stale file:// URLs must not crash workspace load
kind: bug
status: closed
priority: 0
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m2wb8pyw75g2pdfn85aexjyj
parent_id: is-01m2wb8ngskhc23s05wa7tpk9z
created_at: 2026-09-19T08:07:02.128Z
updated_at: 2026-09-19T08:09:27.121Z
closed_at: 2026-09-19T08:09:27.121Z
close_reason: "Fixed in 52023ae: mcp pinned to <2, stale file:// no longer abort identity, prompt/xontrib recover on unexpected exceptions."
resolution: null
duplicate_of: null
---
LocalFileMedia.canonicalize raised FileNotFound for missing temp recordings. item_id() then aborted FileStore reload, so kash xontrib failed. Canonicalize without requiring existence; skip item_id failures; isolate media-service errors.
