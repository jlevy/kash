---
type: is
id: is-01m2wbddbqpe9zyj7gjn9s492r
title: Release kash-shell so uv tool install kash-media gets the startup fixes
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01m2wb8ngskhc23s05wa7tpk9z
created_at: 2026-09-19T08:09:36.886Z
updated_at: 2026-09-19T08:28:24.333Z
closed_at: 2026-09-19T08:28:24.328Z
close_reason: Published kash-shell v0.4.13. PyPI metadata pins mcp<2. uvx kash-shell==0.4.13 reports v0.4.13 with mcp 1.30.0 and StructuredContent.
resolution: null
duplicate_of: null
---
Published kash-shell 0.4.12 still allows mcp 2.x and still crashes on stale file://. After the startup PR merges, tag a new kash-shell release so kash-media installs pick up the pin and resilience fixes.
