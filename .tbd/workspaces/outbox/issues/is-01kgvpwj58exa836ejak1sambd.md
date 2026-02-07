---
created_at: 2026-02-07T09:28:20.391Z
dependencies: []
id: is-01kgvpwj58exa836ejak1sambd
kind: task
labels:
  - tier-3-breaking
priority: 3
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Evaluate extracting web_content as standalone package
type: is
updated_at: 2026-02-07T19:53:48.557Z
version: 3
---
Evaluate extracting web_content/ as a standalone package (e.g. `kash-scraper`). web_content has high independence (9/10 score) with minimal kash dependencies. Would reduce kash core dependency count, make web scraping available to non-kash users, and allow independent versioning/testing. TIER 3 BREAKING: would change `from kash.web_content.X import Y` to new package imports. kash-docs uses canon_url, file_cache_utils, web_extract_readabilipy. Requires migration guide and coordinated release.
