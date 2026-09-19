---
type: is
id: is-01m2wb8qap195ye8smm0d0dvbq
title: Verify kash-media against local kash-shell and fix make build
kind: task
status: closed
priority: 1
version: 3
labels: []
dependencies: []
parent_id: is-01m2wb8ngskhc23s05wa7tpk9z
created_at: 2026-09-19T08:07:03.252Z
updated_at: 2026-09-19T08:12:00.807Z
closed_at: 2026-09-19T08:12:00.807Z
close_reason: "PRs up and CI green: kash-shell https://github.com/jlevy/kash/pull/25 (3.11-3.14 pass); kash-media Makefile https://github.com/jlevy/kash-media/pull/17 (3.13 pass)."
resolution: null
duplicate_of: null
---
kash-media lint/test/build; Makefile uv build must use .venv python; import media kit with editable local kash-shell; load global workspace.
