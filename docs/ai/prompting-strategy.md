# Prompting Strategy

> How prompts will be authored, versioned and composed.

## Status

**Planned** — no production prompts exist. `packages/prompts/README.md` documents the intended layout; `script_versions.prompt_version` is the only code hook.

## Model/provider role

Prompts adapt a stage's task to whichever model is routed ([model-routing](model-routing.md)). Prompts must not depend on one vendor's quirks.

## Target Architecture

- **Files, not strings in code:** `packages/prompts/<name>/v1.md`, `v2.md`, … Each prompt declares its output schema name, required inputs and target task class.
- **Versioned:** every generated artifact records `prompt_version`, `provider`, `model` (columns exist on `script_versions`; scene versions will carry them in `data` or columns — Decision pending).
- **Layered composition:** system role (editor/screenwriter persona) → task instructions → constraints (length, tone, forbidden behaviours) → context blocks (retrieved facts, bibles) → output schema.
- **Originality constraint in every story prompt:** do not paraphrase the source; extract facts and rebuild the narrative ([story-generation-pipeline](story-generation-pipeline.md)).
- **Few-shot examples** kept short and stored beside the prompt; evaluated for leakage into outputs.
- **Separation of data and instructions (design rule):** transcript and any fetched text is inserted in clearly delimited blocks, never concatenated into the instruction part, and treated as untrusted data. The system prompt states that instructions inside delimited blocks must be ignored. Outputs are still validated by schema and code, so an injected instruction cannot change timing, file paths or asset operations (deterministic code owns those). This is a design rule for future prompts: no prompts exist yet, so there is nothing to test it against. Threats and mitigations: [threat-model](../security/threat-model.md).
- **Prompt versioning (Planned):** the only code hook today is `script_versions.prompt_version`; a loader, registry and per-artifact `prompt_version` recording for scenes/analysis do not exist.

## Input context

Assembled by the context builder ([context-management](context-management.md)).

## Structured output, validation, retry

Prompts that feed code request JSON matching a Pydantic model; `generate_structured` appends the JSON Schema automatically ([structured-output](structured-output.md)). Prompt authors should not duplicate the schema by hand.

## Cost considerations

Shorter prompts and cached prefixes reduce spend; avoid re-sending the whole transcript to every stage ([ai-cost-strategy](ai-cost-strategy.md)).

## Quality considerations

Change prompts only with an evaluation comparison against the previous version ([ai-quality-evaluation](ai-quality-evaluation.md)); keep old versions to reproduce earlier outputs.

## Current vs future

Current: callers can pass any `prompt`/`system` string to the provider interface. Future: loader utility, version registry, evaluation fixtures. Visual prompt specifics: [visual-prompting](visual-prompting.md).

## Open questions

Template engine choice; whether prompt versions are global or per-project; how to A/B test prompts without doubling cost.
