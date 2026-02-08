---
close_reason: |-
  AUDIT COMPLETE: 53 files across 7 subdirs (not 72 as spec estimated).

  Structure is well-organized with minimal misplacement:
  - common/ (17): Core utilities, URL, type utils, parsing
  - file_utils/ (12): File ops, format detection, gitignore matching
  - text_handling/ (7): Markdown, normalization, footnotes
  - rich_custom/ (6): Rich library extensions
  - api_utils/ (6): Retry, rate-limiting, async gathering
  - lang_utils/ (2): Capitalization rules
  - file_formats/ (1): Chat format spec

  Hot modules: errors.py (66 imports), file_formats_model.py, url.py, type_utils.py, format_utils.py

  RECOMMENDATION: No reorganization needed — the structure is logical and well-categorized. Only borderline case is s3_utils.py in common/. Breaking changes from moving any of these modules would affect 150+ import statements in downstream packages (kash-docs, kash-media) with no architectural benefit. Keep as-is. If extraction is desired later, start with api_utils/ which is the most self-contained subdir.
closed_at: 2026-02-08T05:01:25.456Z
created_at: 2026-02-07T09:28:20.006Z
dependencies: []
id: is-01kgvpwhs677v9tmymt2z08sc8
kind: task
labels:
  - tier-3-breaking
priority: 3
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: closed
title: Audit and reorganize utils/ directory (72 files across 7 subdirs)
type: is
updated_at: 2026-02-08T05:14:24.670Z
version: 7
---
Audit and reorganize utils/ directory (72 files across 7 subdirs). TIER 3 BREAKING: if any symbols move, kash-docs (uses Url, MarkdownFootnotes, gather_limited, etc in 74 import statements) and kash-media (uses Url, errors, format_utils, etc) must update imports. Requires coordinated release.
