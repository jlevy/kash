---
type: is
id: is-01m2wbddbqpe9zyj7gjn9s492r
title: Release kash-shell so uv tool install kash-media gets the startup fixes
kind: task
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m2wb8ngskhc23s05wa7tpk9z
created_at: 2026-09-19T08:09:36.886Z
updated_at: 2026-09-19T08:09:36.886Z
---
Published kash-shell 0.4.12 still allows mcp 2.x and still crashes on stale file://. After the startup PR merges, tag a new kash-shell release so kash-media installs pick up the pin and resilience fixes.
