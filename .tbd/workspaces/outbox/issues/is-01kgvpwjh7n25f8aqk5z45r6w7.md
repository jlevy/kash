---
created_at: 2026-02-07T09:28:20.774Z
dependencies: []
id: is-01kgvpwjh7n25f8aqk5z45r6w7
kind: task
labels:
  - tier-3-breaking
priority: 3
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: open
title: Evaluate extracting llm_utils as standalone package
type: is
updated_at: 2026-02-07T19:53:48.565Z
version: 3
---
Evaluate extracting llm_utils/ as a standalone package (e.g. `kash-llm`). llm_utils has high independence (8/10 score) and is already a clean LiteLLM wrapper with multi-model support, structured output via Pydantic, citation tracking, and web search integration. TIER 3 BREAKING: would change `from kash.llm_utils.X import Y` to new package imports. Both kash-docs and kash-media use LLM, LLMName, Message, MessageTemplate, llm_template_completion, fuzzy_parsing functions. Requires migration guide and coordinated release.
