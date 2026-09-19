---
type: is
id: is-01m2wb8pyw75g2pdfn85aexjyj
title: Verify kash-shell lint, tests, build, and global workspace load
kind: task
status: closed
priority: 1
version: 5
labels: []
dependencies:
  - type: blocks
    target: is-01m2wb8qap195ye8smm0d0dvbq
  - type: blocks
    target: is-01m2wb8qp5b3yadmpqdc0phrfz
parent_id: is-01m2wb8ngskhc23s05wa7tpk9z
created_at: 2026-09-19T08:07:02.874Z
updated_at: 2026-09-19T08:09:27.442Z
closed_at: 2026-09-19T08:09:27.441Z
close_reason: lint-check 0 errors, 344 tests passed, wheel built, global workspace loads with local kash-shell.
resolution: null
duplicate_of: null
---
make lint-check, full pytest, make build, load ~/Kash/workspace including recording_1.resource.yml, confirm mcp 1.x on a fresh wheel install.
