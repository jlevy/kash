---
type: is
id: is-01m2wb8ngskhc23s05wa7tpk9z
title: Fix kash-media/kash-shell install startup failures
kind: epic
status: open
priority: 0
version: 9
labels: []
dependencies: []
child_order_hints:
  - is-01m2wb8nv8pgy8krq15yh31qy8
  - is-01m2wb8p7hre92tc86j6fdaj0a
  - is-01m2wb8pkfzac86v3nv9q32v7w
  - is-01m2wb8pyw75g2pdfn85aexjyj
  - is-01m2wb8qap195ye8smm0d0dvbq
  - is-01m2wb8qp5b3yadmpqdc0phrfz
  - is-01m2wb8r218w1gmtzq3cpsctnb
  - is-01m2wbddbqpe9zyj7gjn9s492r
created_at: 2026-09-19T08:07:01.400Z
updated_at: 2026-09-19T08:09:36.886Z
---
uv tool install kash-media on Python 3.14 starts kash then fails: mcp 2.x drops StructuredContent, and a stale file:// recording in the global workspace crashes xontrib load, leaving a broken unsubstituted xonsh prompt.
