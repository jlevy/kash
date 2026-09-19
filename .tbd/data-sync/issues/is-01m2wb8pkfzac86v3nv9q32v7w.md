---
type: is
id: is-01m2wb8pkfzac86v3nv9q32v7w
title: Unexpected exceptions must not break the kash prompt or xontrib
kind: bug
status: closed
priority: 0
version: 4
labels: []
dependencies:
  - type: blocks
    target: is-01m2wb8pyw75g2pdfn85aexjyj
parent_id: is-01m2wb8ngskhc23s05wa7tpk9z
created_at: 2026-09-19T08:07:02.510Z
updated_at: 2026-09-19T08:09:27.131Z
closed_at: 2026-09-19T08:09:27.131Z
close_reason: "Fixed in 52023ae: mcp pinned to <2, stale file:// no longer abort identity, prompt/xontrib recover on unexpected exceptions."
resolution: null
duplicate_of: null
---
xonsh treats a raised xontrib exception as a failed load and renders the default prompt template unsubstituted. Install prompt first; never raise from prompt/title; isolate init steps; do not re-raise from the xontrib; last-resort fallback in _get_prompt_tokens.
