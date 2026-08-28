---
type: is
id: is-01m133txk5795m8sata5nbqfxj
title: Web search is a silent no-op for Anthropic models
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-08-28T02:40:28.240Z
updated_at: 2026-08-28T02:40:28.240Z
---
llm_completion accepts enable_web_search, then does two things that together make it inert for Claude models.

1. It gates on litellm.supports_web_search(model=...), which returns False for claude-sonnet-5 and the other Claude names, so the branch never runs. The caller gets one warning line, 'Web search requested but not supported by model claude-sonnet-5', and an otherwise normal completion.
2. Even past that gate it sets completion_params['web_search_options'], the OpenAI-shaped parameter. Anthropic does not read it. Anthropic exposes web search as a server-side tool block.

The capability report is simply wrong. Passing tools=[{'type': 'web_search_20250305', 'name': 'web_search'}] through litellm to claude-sonnet-5 performs real searches and returns a sourced answer in about 11 seconds.

Impact: any kit asking for web search on the default Anthropic profile silently gets none. deep-transcribe hit this in its speaker roster step and now works around it locally, routing on provider and passing the server tool through the existing tools parameter. That workaround should move here so other kits benefit and the local branch can be deleted.

Fix: select the mechanism by provider rather than asking litellm whether search is supported. Anthropic gets the server tool, OpenAI keeps web_search_options. Whatever replaces the gate should fail loudly or report which mechanism was used, since the present failure is invisible.

Not a release blocker for v0.4.10: this is pre-existing, and the downstream workaround functions against 0.4.9.
