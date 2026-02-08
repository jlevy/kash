---
close_reason: |-
  EVALUATION COMPLETE: web_content/ has 10 files (~45KB source).

  KASH DEPENDENCIES (blocking extraction):
  - kash.config.logger, kash.config.settings, kash.config.env_settings
  - kash.model.items_model (Item), kash.model.media_model (MediaType), kash.model.paths_model (StorePath)
  - kash.utils.common.url (Url, is_url, normalize_url, parse_s3_url)
  - kash.utils.errors (FileNotFound, InvalidInput)
  - kash.utils.file_utils (file_format_info, detect_media_type, parse_file_ext)
  - kash.exec.preconditions (is_resource, has_html_body, is_url_resource)
  - kash.media_base.media_services (is_media_url, cache_media, canonicalize_media_url)

  Independence score 9/10 was OVERESTIMATED. Actual: ~5/10. file_cache_utils.py is deeply coupled to kash model layer (Item, StorePath) and media_base. local_file_cache.py uses kash URL utilities extensively.

  RECOMMENDATION: NOT ready for extraction. Would require:
  1. Moving Url NewType + url utilities into a shared package
  2. Removing Item/StorePath dependency from file_cache_utils
  3. Removing media_base dependency (canon_url, file_cache_utils both depend on it)
  4. Replacing ~40 kash.* imports across 10 files

  The coupling to kash model types makes extraction impractical without a larger refactoring effort. Keep in-tree. Consider extraction only after kash.utils.common.url and kash.utils.errors are extracted first.
closed_at: 2026-02-08T05:01:41.055Z
created_at: 2026-02-07T09:28:20.391Z
dependencies: []
id: is-01kgvpwj58exa836ejak1sambd
kind: task
labels:
  - tier-3-breaking
priority: 3
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: closed
title: Evaluate extracting web_content as standalone package
type: is
updated_at: 2026-02-08T18:06:10.894Z
version: 9
---
Evaluate extracting web_content/ as a standalone package (e.g. `kash-scraper`). web_content has high independence (9/10 score) with minimal kash dependencies. Would reduce kash core dependency count, make web scraping available to non-kash users, and allow independent versioning/testing. TIER 3 BREAKING: would change `from kash.web_content.X import Y` to new package imports. kash-docs uses canon_url, file_cache_utils, web_extract_readabilipy. Requires migration guide and coordinated release.
