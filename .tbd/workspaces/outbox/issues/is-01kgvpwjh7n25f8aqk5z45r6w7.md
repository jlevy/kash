---
close_reason: |-
  EVALUATION COMPLETE: llm_utils/ has 10 files (~1,091 lines, ~35.5KB source).

  STANDALONE FILES (no kash imports): init_litellm.py, fuzzy_parsing.py, llm_messages.py
  COUPLED FILES:
  - llm_names.py: imports kash.workspaces.workspaces (dynamic LLM config), kash.shell.output, kash.utils.common.type_utils
  - llm_completion.py: imports kash.config.logger, kash.config.text_styles, kash.utils.common.url, kash.utils.errors, kash.utils.file_formats.chat_format
  - clean_headings.py: imports kash.utils.text_handling.markdown_utils
  - custom_sliding_transforms.py: imports kash.config.logger, kash.utils.common.task_stack, kash.utils.errors

  EXTERNAL DEPS: litellm, openai, pydantic, regex, chopdiff, strif

  CRITICAL BLOCKER: llm_names.py dynamically reads workspace settings to get configured LLM model. This creates a runtime dependency on the workspace system that would need architectural change to break.

  RECOMMENDATION: Partially feasible but premature. To extract:
  1. Replace kash.config.logger with standard logging (trivial)
  2. Replace kash.utils.errors with local error classes (trivial)
  3. Extract kash.utils.common.url.Url type to shared package (shared with web_content)
  4. Decouple llm_names.py from workspace settings (non-trivial — needs config injection)
  5. Replace kash.utils.file_formats.chat_format with local types

  Estimated 3-5 kash.* imports per file need replacement. ~20 total. Feasible as a Tier 3 change but lower priority than kash-8hh2 (standalone runner) which provides more immediate value.
closed_at: 2026-02-08T05:01:58.007Z
created_at: 2026-02-07T09:28:20.774Z
dependencies: []
id: is-01kgvpwjh7n25f8aqk5z45r6w7
kind: task
labels:
  - tier-3-breaking
priority: 3
spec_path: docs/project/specs/active/plan-2026-02-06-code-review-architecture.md
status: closed
title: Evaluate extracting llm_utils as standalone package
type: is
updated_at: 2026-02-08T16:58:13.770Z
version: 7
---
Evaluate extracting llm_utils/ as a standalone package (e.g. `kash-llm`). llm_utils has high independence (8/10 score) and is already a clean LiteLLM wrapper with multi-model support, structured output via Pydantic, citation tracking, and web search integration. TIER 3 BREAKING: would change `from kash.llm_utils.X import Y` to new package imports. Both kash-docs and kash-media use LLM, LLMName, Message, MessageTemplate, llm_template_completion, fuzzy_parsing functions. Requires migration guide and coordinated release.
