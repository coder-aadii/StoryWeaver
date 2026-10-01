# AI Evaluation (Testing)

> How non-deterministic AI output should be tested. Product-level quality design lives in [AI quality evaluation](../ai/ai-quality-evaluation.md).

## Status

Planned — not implemented. No generation pipeline exists, so there is nothing to evaluate yet.

## What is tested today

Only plumbing: structured-output parsing/retry with fake providers ([unit testing](unit-testing.md)). No prompt has been run against a real model in this project.

## Target approach

1. **Schema validity rate** — fraction of responses passing `generate_structured` validation without retry, per provider/model.
2. **Golden source set** — a small, curated set of source transcripts (user-authorised content) with expected properties (not expected text): story candidates are independent, structure beats present, scenes serve story, no verbatim overlap above a threshold.
3. **Originality/similarity checks** — measure overlap of generated scripts with source text (n-gram/embedding similarity). This is a **quality metric, not a legal guarantee**; StoryWeaver makes no claim that output is copyright-safe ([content policy](../product/content-policy-and-source-usage.md)).
4. **Regression across model changes** — rerun the golden set when switching providers/models ([model routing](../ai/model-routing.md)).
5. **Human review** for creative quality; LLM-as-judge only as a cheap pre-filter, itself spot-checked.

Opt-in (cost, nondeterminism), never part of default `make test`. Decision pending on tooling.
