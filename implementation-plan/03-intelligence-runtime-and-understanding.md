# P2 Intelligence Runtime and P3 Source Understanding

> Concrete tasks for the shared AI runtime (persisted jobs, provider hardening, routing, cache, usage, prompts, artifacts) and the first AI stage built on it (source understanding and narrative opportunities).

## Status

Planned. Current state (verified in code): provider interfaces and five LLM adapters exist and are only partly mock-tested; there are no prompts, no persisted jobs, no usage records, no cache, no routing beyond per-task model *settings*, and no application code calls an LLM. See [status](../docs/reference/status.md) and [Known issues](../docs/reference/status.md#known-issues-and-limitations). Master contract: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) (phases, checkpoints C0 and C, decisions D1–D3, D9). Prerequisite phases: [`01-foundation.md`](01-foundation.md) (P0) and [`02-source-library.md`](02-source-library.md) (P1).

**What exists today (inspected):**

| Area | Reality |
| --- | --- |
| `app/intelligence/providers/base.py` | `LLMProvider.generate` wraps only `httpx.HTTPError` (KI-3); `generate_structured` = JSON-Schema-in-prompt + one retry on `ValidationError`/`ValueError`; `http_client` hard-codes a 120 s timeout; no token/cost/cache/run awareness |
| `app/intelligence/registry.py` | `get_llm(name)` / `get_embeddings(name)` / `llm_status()`; no task routing, no fallback |
| `app/core/config.py` | `default_llm_provider="ollama"`, `default_llm_model=""`, per-task `*_llm_model` strings, `model_for(task)`; no timeout/retry/route/price settings |
| `app/core/logging.py` | substring redaction masks `output_tokens` (KI-2) |
| `app/workflows/runner.py` | `LocalRunner` (ThreadPoolExecutor(2)), returns a string id, **no DB state**, nothing calls `submit` |
| `packages/prompts/` | README only |
| Tables | `topics` (unique name/slug, no source link table), `transcripts`, `transcript_chunks`; **no** `workflow_runs`, `llm_calls`, `artifacts` |
| Tests | `tests/test_units.py` has one mocked-HTTP test (Ollama chat); `generate_structured` is tested via a fake provider only |

## Shared design recap (do not redefine; link instead)

- AI vs code split: [ADR-004](../docs/decisions/ADR-004-ai-vs-deterministic-responsibilities.md). Routing target design: [model routing](../docs/ai/model-routing.md). Cost gating: [AI cost strategy](../docs/ai/ai-cost-strategy.md). Prompt/validation target: [prompting strategy](../docs/ai/prompting-strategy.md), [structured output](../docs/ai/structured-output.md), [context management](../docs/ai/context-management.md). Idempotency keys table: [retry and recovery](../docs/workflows/retry-and-recovery.md). Staleness semantics (input-hash comparison): [`versioning-and-invalidation.md`](versioning-and-invalidation.md) — **this file creates the `artifacts` tables and service scaffolding only; it does not define when something is stale.**
- Task names used for routing: `classification`, `analysis`, `story`, `script`, plus `repair` (structured-output repair). Settings already name four of them; P2 adds the routing layer around them.

---

# Part A — Phase P2: Intelligence runtime

## Goal

Every later AI stage (P3–P7) is built on **one tested runtime**: jobs that are persisted, idempotent and recoverable; provider failures that are classified instead of leaking raw exceptions; one place where model/provider is chosen (routing + fallback); every call cached, recorded and costed; prompts versioned as files; AI outputs stored as versioned, schema-validated artifacts. Verified by Checkpoint **C0** ([master](IMPLEMENTATION_PLAN.md#checkpoints-objective)).

## Why now

P3 is the first stage that spends tokens. Building it ad hoc would put persistence, retry, caching and cost accounting in five divergent places (P3, P4, P5, P6 prompts, P7). The runtime is also fully testable with a fake provider, so it carries no spend and no external dependency. KI-2 (token logging) and KI-3 (error wrapping) must be closed before the usage records and retry logic are meaningful.

## Prerequisites

- P0 acceptance criteria met ([`01-foundation.md`](01-foundation.md)): `TEST_DATABASE_URL` guard (KI-19), engine-cache isolation in tests (KI-11), `StoryWeaverError`→HTTP handler (KI-8), `Settings.embedding_dimensions` guard decided (KI-6), PATCH null/length handling (KI-4). **If P0 triage already closed KI-2 or KI-3, tasks P2-T2/P2-T3 reduce to confirming the described tests exist.**
- P1 delivered ([`02-source-library.md`](02-source-library.md)): current transcript + `transcript_chunks`, `fingerprint`, source usage records, **and the `workflow_runs` table with a thin `RunService`** (`app/workflows/runs.py`, `RunStatus` enum, `GET /runs/{id}` and `GET /runs`) already running `source.add`/`source.fetch_transcript` on `LocalRunner`. **P2-T4 therefore extends that table, service and router — it does not create a second one** (D1): it adds the missing columns, the `cancelled` status, startup reconciliation, the retry/cancel endpoints and generic registry/progress handling, in an ALTER-only migration.
- Postgres with pgvector reachable (`TEST_DATABASE_URL`); no real provider required for any P2 test.

## Backend

New and changed modules (confirm against the tree before editing; paths follow existing `app/<domain>/` naming):

| Path | Mark | Purpose |
| --- | --- | --- |
| `apps/api/app/core/errors.py` | MODIFY | Add `ProviderTimeoutError`, `ProviderRateLimitError`, `ProviderAuthError`, `ProviderResponseError` (all subclass `ProviderError`), plus `retriable: bool` class attribute |
| `apps/api/app/core/logging.py` | MODIFY | Redaction by exact-key set + suffix rules (KI-2) |
| `apps/api/app/core/config.py` | MODIFY | New settings (see below) |
| `apps/api/app/intelligence/providers/base.py` | MODIFY | Classify every failure; configurable timeout; keep `generate`/`generate_structured` signatures backward compatible |
| `apps/api/app/intelligence/providers/fake.py` | NEW | `FakeLLMProvider` for tests/e2e |
| `apps/api/app/intelligence/routing.py` | NEW | `resolve_route(task) -> list[Route]`, fallback chain |
| `apps/api/app/intelligence/gateway.py` | NEW | `AIGateway.complete(...)` / `.complete_structured(...)`: the **only** entry point domain code uses; applies routing, cache, retry, repair, usage recording |
| `apps/api/app/intelligence/prompts.py` | NEW | Prompt registry loader (files under `packages/prompts/`) |
| `apps/api/app/intelligence/pricing.py` | NEW | Cost estimate from a configured price table |
| `apps/api/app/workflows/runs.py` | MODIFY (created in P1) | Extend `RunService`: submit-by-idempotency-key semantics for all kinds, retry, cancel, `reconcile_interrupted`, progress updates |
| `apps/api/app/workflows/registry.py` | NEW | `WORKFLOWS: dict[kind, callable]` — kinds are the shared names in the master plan |
| `apps/api/app/workflows/runner.py` | MODIFY | `LocalRunner.submit` accepts a caller-supplied id (the run id) so logs/DB agree; unchanged protocol otherwise |
| `apps/api/app/artifacts/` (`kinds.py`, `service.py`) | NEW | Kind→Pydantic model registry; create version, approve, record dependencies, read current |
| `apps/api/app/models/intelligence.py` | NEW | `LLMCall`, `Artifact`, `ArtifactDependency` models; imported from `app/models/__init__.py` (MODIFY). `WorkflowRun` stays where P1 put it (`models/domain.py`) |
| `apps/api/app/main.py` | MODIFY | Startup hook: `RunService.reconcile_interrupted()`; exception handler registration (from P0) |
| `scripts/benchmark_llm.py` | NEW | Hardware/model benchmark harness (P2-T1) |

New settings (all optional; app must still boot with none set — add to `.env.example` and [environment reference](../docs/reference/environment-reference.md) at phase end):

| Setting | Purpose |
| --- | --- |
| `LLM_ROUTES` | JSON: task → ordered list of `{provider, model, timeout_s?, max_tokens?, temperature?, context_tokens?, escalate_on_invalid?}`. Falls back to `default_llm_provider`/`model_for(task)` when absent, so existing config keeps working |
| `LLM_TIMEOUT_SECONDS`, `LLM_MAX_ATTEMPTS`, `LLM_BACKOFF_BASE_SECONDS` | Defaults for retry policy (route can override timeout) |
| `LLM_PRICE_TABLE` | JSON `{"provider:model": {"in_per_1k": x, "out_per_1k": y}}`; absent entry ⇒ `cost_estimate` is NULL (not zero, not guessed); local providers may be configured as 0 |
| `ENABLE_FAKE_LLM` | Registers provider name `fake` in the registry (default false) |
| `RUN_MAX_WORKERS` | `LocalRunner` pool size (default current 2) |

## Database

One Alembic revision `p2_intelligence_runtime` (review the autogenerate output; run `upgrade → downgrade → upgrade` + `alembic check`). Enums stay VARCHAR(32) like existing tables ([database schema](../docs/data/database-schema.md)).

**`workflow_runs` (EXISTS from P1 — ALTER only, D1).** P1 created: `id, kind, subject_type, subject_id, status (queued/running/succeeded/failed/interrupted), attempt, idempotency_key UNIQUE, params, progress, error JSONB {code,message,retryable}, started_at, finished_at, timestamps`, indexed on `(subject_type, subject_id)` and `status`. **P2 adds:** `project_id` UUID NULL FK→projects ON DELETE CASCADE (indexed), `result` JSONB NULL (ids of produced artifacts), `max_attempts` int, `cancel_requested` bool default false, and the status value `cancelled` (VARCHAR column; extend the `RunStatus` enum). It **reuses** P1's `attempt` and `error` JSONB (`error.code` is the machine code; no separate `error_code` column). Add index `(subject_type, subject_id, created_at desc)` only if P1 did not.

**`llm_calls` (NEW, D2)** — `id`, `run_id` FK→workflow_runs SET NULL idx, `project_id` FK NULL idx, `source_video_id` FK NULL idx, `task` VARCHAR(32), `provider`, `model`, `prompt_name`, `prompt_version`, `request_hash` CHAR(64), `attempt` int, `status` (`ok|cache_hit|invalid_output|provider_error`), `request_chars` int, `response_text` Text NULL, `response_json` JSONB NULL (parsed, validated), `input_tokens` int NULL, `output_tokens` int NULL, `duration_ms` int NULL, `cost_estimate` Numeric(12,6) NULL, `cache_of_id` FK self NULL, `error_type` VARCHAR(64) NULL, `error` Text NULL, `created_at`. **Partial index** for cache lookup: `(task, provider, model, prompt_name, prompt_version, request_hash) WHERE status='ok'`. D2 specified `(task, model, prompt_version, request_hash)`; this plan adds `provider` and `prompt_name` (a superset, avoids cross-prompt collisions) — see Decision points. *(Naming: `request_hash` is the hash of the rendered provider request; it is deliberately not called `input_hash`, which in [versioning-and-invalidation.md](versioning-and-invalidation.md) means the hash of declared upstream **inputs** of an artifact.)*

**`artifacts` (NEW, D3)** — `id` UUID PK (each *version* is a row), `family_id` UUID idx (id of the first version; groups versions of one logical artifact), `version` int, `kind` VARCHAR(48) idx (validated against the kind registry, not a DB enum), `project_id` FK NULL, `source_video_id` FK NULL (both ON DELETE CASCADE), CHECK `(project_id IS NOT NULL OR source_video_id IS NOT NULL)`, `status` (`draft|ready|approved|superseded|failed`), `origin` (`ai|user_edit`), `data` JSONB, `schema_version` int, `input_hash` CHAR(64) NULL, `produced_by_run_id` FK→workflow_runs SET NULL, `meta` JSONB (llm_call ids, route used), `approved_at` timestamptz NULL, `approved_by` VARCHAR(64) NULL, `is_current` bool. Constraints: **UNIQUE `(family_id, version)`**; **partial UNIQUE `(family_id) WHERE is_current`**. Index `(project_id, kind)` and `(source_video_id, kind)`.

**`artifact_dependencies` (NEW, D3)** — `artifact_id` FK CASCADE, `upstream_type` VARCHAR(32) (`artifact|transcript|script_version|scene_version|asset`), `upstream_id` UUID, `upstream_hash` CHAR(64) NULL; PK `(artifact_id, upstream_type, upstream_id)`. Rows record *what a version was built from*; how they are compared to detect staleness is defined in [`versioning-and-invalidation.md`](versioning-and-invalidation.md).

No existing table is altered in P2. Retention of `response_text` (large) is **Decision pending**; default keep, prune policy in P10.

## API

All routes: auth none (localhost only, D14); errors via the P0 exception handler (404 unknown id, 409 invalid state, 422 validation).

| Endpoint | Method | Purpose / contract |
| --- | --- | --- |
| `/api/v1/runs/{run_id}` | GET | Run state: status, progress, attempts, error, result ids. Used by UI polling (D13) |
| `/api/v1/runs` | GET | Filter `subject_type`, `subject_id`, `kind`, `status`, `limit/offset` (same pagination rules as existing lists) |
| `/api/v1/runs/{run_id}/retry` | POST | Only from `failed`/`interrupted`; re-queues the same run (attempts+1). 409 otherwise. Idempotent: retry of a `queued/running` run returns it unchanged |
| `/api/v1/runs/{run_id}/cancel` | POST | Sets `cancel_requested`; workflow stops at the next step boundary → `cancelled`. 409 if finished |
| `/api/v1/artifacts` | GET | Filter `source_video_id`, `project_id`, `kind`, `current=true` |
| `/api/v1/artifacts/{id}` | GET | One artifact version |
| `/api/v1/artifacts/{id}/versions` | GET | All versions in the family, newest first |
| `/api/v1/artifacts/{id}/versions` | POST | Body `{data}`: create a **new user-edit version**; validated by the kind's Pydantic model; 422 on schema failure; 409 if `id` is not the current version (edit the current one) |
| `/api/v1/artifacts/{id}/approve` | POST | Sets `status=approved`, `approved_at`; idempotent. Used by P4+ gates; no semantics added here |
| `/api/v1/sources/{id}/usage`, `/api/v1/projects/{id}/usage` | GET | Aggregates over `llm_calls`: calls, cache hits, input/output tokens, cost estimate (NULL-aware), by task and model |

No endpoint accepts a provider or model from the client; routing is server configuration.

## Frontend

Minimal in P2 (Studio comes in P9): a reusable `RunStatus` component and a `useRun(runId)` hook (TanStack Query, `refetchInterval` while status is `queued|running`, stops on terminal states) — **NEW** `apps/web/src/components/run-status.tsx`, `apps/web/src/lib/runs.ts`; `apps/web/src/lib/api.ts` **MODIFY** to surface the API `detail` message in `ApiError` (documented gap). The Settings page (**MODIFY** `apps/web/src/app/settings/page.tsx`) shows resolved routes per task (provider/model, configured yes/no) from a new `GET /api/v1/health/providers` field (additive; never exposes keys). Vitest: `useRun` stops polling on terminal state; `RunStatus` renders each status.

## Services/Workflows

**Run state machine** (deterministic; the model never sets status):

```
queued → running → succeeded
              ↘ failed → (retry) → queued
              ↘ cancelled
running --(process restart)--> interrupted → (retry) → queued
```

- `RunService.submit(kind, idempotency_key, params, subject, project_id)` (P1's service, extended):
  1. Insert-or-get by `idempotency_key` (unique). If an existing run is `queued|running|succeeded` → return it (`reused=true`, no new execution). If `failed|interrupted|cancelled` → treat as retry (attempts+1) only when called via the retry endpoint or `force`; plain re-submit of a failed key returns the failed run with its error.
  2. Hand `(run_id)` to `LocalRunner`; the workflow function (registered in `workflows/registry.py`) **opens its own DB session**, loads the run, executes steps, updates `progress` after each step, checks `cancel_requested` between steps, writes `status/result/error`.
- Startup `reconcile_interrupted()`: all `running` and `queued` rows (in-memory queue is lost on restart) → `interrupted` with `error.code=process_restart`. Nothing is auto-resumed in the MVP; the user (or a P10 policy) retries. Workflow functions must therefore be **resumable by re-execution**: each step checks whether its output (artifact with matching `input_hash`, cached `llm_calls`) already exists and skips it.
- Error boundary: any exception → `failed` with `error.code` from the error class and a *sanitized* message (no prompts, no keys). The existing `LocalRunner` logging stays; the runner remains a thin executor.

**AIGateway** (single call path, all in code):

1. `route = resolve_route(task)` → ordered candidates (config or fallback to `model_for(task)`).
2. Render the prompt from the registry → `request_hash = sha256(canonical_json({system, user, schema_name, schema_json, temperature, max_tokens}))`.
3. Cache lookup in `llm_calls` (`status='ok'`, same task/provider/model/prompt name+version/hash) → on hit insert a `cache_hit` row (zero tokens, `cache_of_id`) and return the stored `response_json`. `force=True` bypasses.
4. Call the provider with route timeout. Retry **retriable** errors (`ProviderTimeoutError`, `ProviderRateLimitError`, 5xx-class `ProviderError`) up to `LLM_MAX_ATTEMPTS` with exponential backoff + jitter (injectable `sleep`/`random` so tests are instant and deterministic). `ProviderAuthError`, `ProviderNotConfiguredError` are not retried but **do** advance to the next route candidate.
5. Structured calls: parse via `extract_json` → validate with the Pydantic schema; on failure make **one repair call** (original prompt + the validation error, task `repair`, same route), then if the route sets `escalate_on_invalid`, try the next candidate; otherwise raise `ProviderResponseError`. Every attempt is an `llm_calls` row.
6. Record tokens, duration, `cost_estimate` (price table; NULL if unknown). Return the typed object plus a `CallInfo` (provider, model, cached, tokens) for artifact `meta`.

## AI

P2 itself adds no AI content stage. AI responsibilities start in P3. P2's AI-adjacent deliverables are *infrastructure*:

- **Prompt registry** (files under `packages/prompts/`, D-contract): per prompt a directory `packages/prompts/<prompt_name>/v1/` with `meta.toml` (name, version, task, `output_schema` dotted Python path, declared variables, description), `system.md`, `user.md`. Templating via stdlib `string.Template` with a loader check that the declared variables equal the placeholders (no new dependency; `tomllib` is stdlib on Python 3.12). Released versions are **immutable**: `packages/prompts/prompts.lock` (NEW) stores a content hash per released `<name>/<version>`; a test fails if a released version changes (create `v2` instead). `prompt_version` is recorded on every `llm_calls` row and artifact `meta`.
- **Routing config** as above; example only (never defaults in code): `LLM_ROUTES='{"analysis":[{"provider":"google","model":"<chosen after benchmark>"},{"provider":"ollama","model":"<local>"}]}'`.
- **Fake provider** (`providers/fake.py`): returns canned responses keyed by `prompt_name` from `apps/api/tests/fixtures/ai/<prompt_name>/<case>.json` (NEW dir), can be told to fail N times / return invalid JSON / time out. Enabled by `ENABLE_FAKE_LLM`; used by pytest and Playwright. Golden fixtures are **recorded real outputs reviewed by a human** (`scripts/benchmark_llm.py --record`), clearly labelled as such.
- **Hardware/model benchmark (P2-T1)** — see tasks.

## Storage/media

None beyond prompt files in the repository. `llm_calls.response_text` stays in Postgres (text). No binary data.

## Tasks

| ID | Task | Files | Steps | Verified by |
| --- | --- | --- | --- | --- |
| **P2-T1** | **Benchmark spike** (do first; informs routing defaults, D9) | `scripts/benchmark_llm.py` NEW; sample text fixture `apps/api/tests/fixtures/transcripts/` NEW (self-written or public-domain, ~5k words) | Harness takes `--provider --model`, runs N=10 structured extractions of the P3 `WindowExtraction` schema against windows of the sample; records tokens/s, wall time per window, JSON-valid-first-try rate, repair rate, peak RSS delta (`/proc`); writes JSON to `data/temporary/benchmarks/` (git-ignored). **Do not run as part of the plan authoring; the user runs it with their providers.** Ollama is not installed on the original dev machine, so local numbers are *unmeasured* | Script runs against the fake provider in a unit test; real numbers are produced by the user, not assumed. Publishing results is done only when asked |
| P2-T2 | Fix **KI-2**: redaction | `core/logging.py` MODIFY; `tests/test_logging.py` NEW | Replace substring match with an exact sensitive-key set (`api_key`, `authorization`, `password`, `secret`, `token`, `access_token`, `refresh_token`, `x-api-key`, `credential(s)`) and an explicit allowlist (`input_tokens`, `output_tokens`, `max_tokens`, `total_tokens`); unit-test both directions | `output_tokens=5` is logged as 5; `api_key="x"` and nested `headers.authorization` still redacted |
| P2-T3 | Fix **KI-3**: classify provider failures; configurable timeout | `core/errors.py`, `providers/base.py`, each adapter (`ollama.py`, `google.py`, `openai_compatible.py`, `claude_compatible.py`) MODIFY | In `generate`: catch `httpx.TimeoutException`→Timeout, `HTTPStatusError` 401/403→Auth, 429→RateLimit, ≥500→retriable `ProviderError`, other 4xx→non-retriable; catch `KeyError/IndexError/TypeError/ValueError/JSONDecodeError` from `_complete` (incl. Google no-`candidates`) → `ProviderResponseError`; `http_client(timeout=)` param; no secrets in messages | Shared contract test (below) |
| P2-T4 | **Extend** P1's `workflow_runs`/`RunService`: new columns, `cancelled`, reconciliation, retry/cancel, generic workflow registry, run API | `models/domain.py` + `models/enums.py` MODIFY, `workflows/runs.py` MODIFY, `workflows/registry.py` NEW (MODIFY if P1 already added one), `workflows/runner.py` MODIFY, `api/v1/runs.py` MODIFY (P1 created the GETs), `main.py` MODIFY, ALTER-only migration | Implement as specified under *Services/Workflows*; register a trivial `noop.sleep` kind for tests | Tests in *Testing*; Checkpoint C0 items 1–2 |
| P2-T5 | `llm_calls` + `AIGateway` (cache, retry/backoff, repair, usage, cost) | `intelligence/gateway.py`, `pricing.py` NEW, models, migration | As specified; gateway never imports a vendor adapter, only the registry | Gateway tests; second identical call ⇒ 0 provider calls |
| P2-T6 | Routing | `intelligence/routing.py` NEW, `config.py` MODIFY, `registry.py` MODIFY (add `fake` when enabled) | Parse `LLM_ROUTES`; validate at first use (not at import); fallback to legacy settings; `GET /health/providers` additive fields | Routing tests: fallback order, unconfigured provider skipped, legacy settings still work |
| P2-T7 | Prompt registry + lock file | `intelligence/prompts.py` NEW, `packages/prompts/README.md` MODIFY, `packages/prompts/prompts.lock` NEW | Loader, variable check, hash lock test; ship one trivial test prompt only under `apps/api/tests/fixtures/prompts/` (real prompts arrive in P3) | Mutating a released prompt fails the lock test |
| P2-T8 | Fake provider + fixtures | `providers/fake.py` NEW, `tests/fixtures/ai/` NEW | See *AI* | Used by T4–T6 tests |
| P2-T9 | `artifacts` + `artifact_dependencies` + service + generic API | `models/intelligence.py`, `artifacts/kinds.py`, `artifacts/service.py`, `api/v1/artifacts.py` NEW, migration | `create_version(kind, owner, data, input_hash, deps, run_id, origin)` validates `data` with the kind model, sets `version=max+1`, flips `is_current` atomically in one transaction (old row → `superseded`), writes dependency rows; `approve()`; read-current helpers. Kind registry initially empty except a test kind; P3 registers the first two | Concurrency test: two simultaneous `create_version` ⇒ distinct versions, exactly one current |
| P2-T10 | Usage aggregation endpoints | `api/v1/usage.py` NEW | SQL aggregates over `llm_calls`; NULL-aware cost sum | API test with seeded rows |
| P2-T11 | Provider contract test suite | `tests/contract/test_llm_provider_contract.py` NEW | Parametrised over Ollama/Google/OpenRouter/Grok/Claude-compatible using `httpx.MockTransport` (patched `httpx.Client`, as the existing test does): success shape and token parsing, 401, 429, 500, timeout, malformed 200 (missing keys / empty `candidates`), unknown model, no secret in exception text | All adapters pass; **this proves request/response handling against mocks only — not live behavior** |
| P2-T12 | Web: `useRun`, `RunStatus`, `ApiError.detail`, settings routes view | see *Frontend* | | Vitest |
| P2-T13 | Docs + status | `docs/` per list below | | Reviewed against code |

## Testing

- **Unit:** exact-key redaction; error classification table; backoff schedule with injected sleep; input-hash canonicalisation (key order independence); price calculation incl. unknown model ⇒ NULL; prompt loader and lock; route parsing.
- **Database:** constraint tests — `workflow_runs.idempotency_key` unique, `artifacts` `(family_id, version)` unique and single-current partial index, CHECK owner, FK cascades; migration up/down/up + `alembic check`.
- **Workflow (fake provider):** (a) submit twice with same key ⇒ one run, one execution (regression: P1's `source.add` run behaviour unchanged); (b) injected failure ⇒ `failed`, error persisted, retry ⇒ succeeds, attempts=2; (c) simulate restart: run in `running` ⇒ `reconcile_interrupted` ⇒ `interrupted` ⇒ retry completes without repeating cached calls; (d) cancel mid-run stops at step boundary; (e) a failing run never alters unrelated rows.
- **Gateway:** cache hit costs 0 calls and records `cache_hit`; `force` bypasses; invalid JSON ⇒ one repair call ⇒ success or `ProviderResponseError`; fallback to second route on `ProviderAuthError`; every attempt recorded.
- **API:** runs/artifacts/usage endpoints incl. 404/409/422; edit of non-current artifact ⇒ 409.
- **Frontend:** Vitest for `useRun`/`RunStatus`.
- **Not claimed:** no live-provider test. The benchmark script is the only path that touches real providers and it is user-run.

## Observability

Log events (JSON, never prompts or keys): `run.created|started|step|finished|failed|interrupted|cancelled` with `workflow_id`(=run id), `kind`, `project_id`, `source_id`, `status`, `duration`, `error_code` (log field; persisted as `error.code`); `llm.call` with `provider`, `model`, `task`, `prompt_name`, `prompt_version`, `input_tokens`, `output_tokens` (visible after P2-T2), `duration`, `cached`, `attempt`, `status`. The `llm_calls` table is the durable record; the usage endpoints are the first cost view. Tracing/metrics stacks are out of scope.

## Failure handling & idempotency

Run idempotency key convention: `"<kind>:<subject_id>:<input-version-fingerprint>"` (specific keys per workflow are defined in each phase; the cross-phase table lives in [retry and recovery](../docs/workflows/retry-and-recovery.md)). Provider calls are idempotent by `input_hash` cache. Artifact creation is idempotent by `(family, input_hash)`: creating a version whose `input_hash` equals the current version's returns the current version (no duplicate). A failed run leaves previously current artifacts untouched.

## AI vs deterministic responsibilities (P2)

AI: nothing is decided by a model in P2. Deterministic code: routing, hashing, caching, retry/backoff, status transitions, version numbers, `is_current`, approval timestamps, cost arithmetic, prompt version pinning.

## Acceptance criteria (Checkpoint C0)

1. `make lint` clean; `make test` green with `TEST_DATABASE_URL` (DB tests ran, not skipped).
2. A `noop`/fake-provider workflow submitted via the service runs as a persisted `workflow_runs` row; resubmitting the same key creates no second execution.
3. After a simulated restart the row is `interrupted`; `POST /runs/{id}/retry` completes it without repeating cached provider calls.
4. A second identical gateway call makes **zero** provider calls (`cache_hit` row recorded); `force` makes one.
5. All five LLM adapters pass the provider contract suite (mock transport); no raw `KeyError/IndexError/JSONDecodeError` escapes `generate`.
6. `output_tokens` appears in logs as a number; `api_key`/`authorization` still masked.
7. `GET /api/v1/projects/{id}/usage` and `/sources/{id}/usage` return calls, cache hits, tokens, and cost (NULL when no price configured).
8. Creating a second version of an artifact leaves exactly one `is_current`; concurrent creation does not duplicate versions.
9. With a **real** provider configured by the user, `scripts/benchmark_llm.py` completes and a structured call succeeds once (manually recorded; not part of automated gates).
10. Docs updated; no provider/model name hard-coded in code.

## Deliverables

Migration `p2_intelligence_runtime` (new tables + ALTER of `workflow_runs`); modules listed under *Backend*; prompt registry + lock; fake provider + fixtures; contract suite; run/artifact/usage APIs; `useRun`/`RunStatus`; benchmark script; updated docs.

## Dependencies

Depends on P0, P1. Required by P3, P4, P5, P6, P7, P8, P9, P11. Does not depend on P3.

## Do NOT

- Do not let domain code call a provider adapter directly; use `AIGateway`.
- Do not add Temporal, Redis, Celery, a message queue or a separate cache service (D1/D2 use Postgres).
- Do not put provider names or model ids in code defaults; do not assume a local model is fast enough — read the benchmark.
- Do not auto-resume interrupted runs in the MVP, or log prompts/responses at INFO.
- Do not define staleness rules here ([`versioning-and-invalidation.md`](versioning-and-invalidation.md) owns them).

## Docs to update at phase end

[status](../docs/reference/status.md) rows: LLM provider layer, model routing, cost tracking, caching, prompt versioning, provider failure isolation, artifact versioning; remove KI-2/KI-3 only when fixed and tested; [model routing](../docs/ai/model-routing.md), [prompting strategy](../docs/ai/prompting-strategy.md), [structured output](../docs/ai/structured-output.md), [workflow overview](../docs/workflows/workflow-overview.md), [retry and recovery](../docs/workflows/retry-and-recovery.md), [story data model](../docs/data/story-data-model.md) (record decision D3), [API docs](../docs/api/README.md) (runs, artifacts, usage), [environment reference](../docs/reference/environment-reference.md), [testing strategy](../docs/testing/testing-strategy.md), [changelog](../docs/reference/changelog.md).

---

# Part B — Phase P3: Source understanding and narrative opportunities

## Goal

For a stored source, produce — **in stages, not one prompt** — an inspectable, grounded, editable analysis (facts, events, entities, dates, causes, consequences, conflicts, discoveries, mysteries, surprising facts, turning points, themes/topics) and a set of **narrative opportunities** (independent story arcs; possibly none). Checkpoint **C**.

## Why now

Everything downstream (candidates, script) consumes this representation instead of raw transcript text ([research and intelligence](../docs/domains/research-and-intelligence.md), [story generation pipeline](../docs/ai/story-generation-pipeline.md)). It is the cheapest AI stage to validate (one source, no approval gate, no media) and exercises the whole P2 runtime end to end. Opportunities are produced here but *selected* in P4 — keeping analysis reusable across many future projects (source reuse).

## Prerequisites

P2 complete; P1 delivered a current transcript and chunks for a source. The route table for `analysis` and `classification` configured (real or fake). Benchmark results (P2-T1) consulted for window size — the plan does not assume a context size: each route may declare `context_tokens`, and windowing derives from it.

## Backend

| Path | Mark | Purpose |
| --- | --- | --- |
| `apps/api/app/intelligence/understanding/schemas.py` | NEW | Pydantic models (below), `extra="forbid"`, bounded string lengths and list sizes |
| `apps/api/app/intelligence/understanding/windows.py` | NEW | Deterministic windowing of chunks |
| `apps/api/app/intelligence/understanding/stages.py` | NEW | The four stage functions (pure given gateway results) + code-side validators/mergers |
| `apps/api/app/intelligence/understanding/workflow.py` | NEW | `source.analyze` workflow function registered in `workflows/registry.py` |
| `apps/api/app/intelligence/understanding/topics.py` | NEW | Slug/normalise/match proposed topics to `Topic` rows |
| `apps/api/app/artifacts/kinds.py` | MODIFY | Register `source_analysis`, `narrative_opportunity_set` |
| `packages/prompts/source_extraction/v1/`, `source_synthesis/v1/`, `source_topics/v1/`, `narrative_opportunities/v1/` | NEW | Prompt files + `prompts.lock` entries |
| `apps/api/app/models/intelligence.py` | MODIFY | `SourceVideoTopic` link model |
| `apps/api/app/api/v1/understanding.py` | NEW | Source-scoped routes below |

### Stage definitions

Task names: extraction/synthesis/opportunities use route task **`analysis`**; topic assignment uses **`classification`** (cheaper/local candidate). Grounding reference type used everywhere: `Ref {chunk_index:int, start:float|None, end:float|None}` — resolved by code from `transcript_chunks`; the model supplies **only `chunk_index`**, never timestamps (code fills times).

| # | Stage | Input | Output schema (fields) | Persistence | Validation (code) | Cache key | Retry |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S0 | **Prepare** (code only) | current transcript chunks | `Window[] {window_id, chunk_start, chunk_end, text}` | not persisted (recomputable) | windows cover every chunk exactly once; size ≤ route `context_tokens` budget (chars/4 heuristic, labelled heuristic); single window if the whole transcript fits | n/a | n/a |
| S1 | **Extract** (map; AI) | one window | `WindowExtraction {facts[{text, refs[chunk_index]}], events[{text, when_text?, refs}], entities[{name, kind(person/place/org/object/concept), refs}], statements?}` | `llm_calls` only (cache) | every `chunk_index` ∈ window; ≤ N items; strings ≤ max length; unknown fields rejected | prompt `source_extraction@v1` + window text hash | gateway retry + repair; a window that still fails marks the run `failed` at that step (resumable) |
| S2 | **Synthesise** (reduce; code then AI) | all `WindowExtraction`s | `SourceAnalysis {summary, facts[{id,text,refs}], events[{id,text,when_text?,order,refs}], entities[{id,name,kind,aliases}], relations[{kind: cause\|consequence\|conflict\|discovery\|mystery\|surprise\|turning_point, from_id, to_id?, note, refs}], key_dates[...]}` | artifact `source_analysis` (v1, origin `ai`) | **code first:** assign ids (`f001`, `e001`…), exact/normalised-name dedupe of entities, chronological `order` from earliest ref; **AI** only proposes merges and `relations`; validator rejects relations pointing at unknown ids or refs outside the transcript | `source_synthesis@v1` + hash of the merged S1 outputs | as above |
| S3 | **Themes/topics** (AI, cheap) | `SourceAnalysis.summary` + fact/event texts (not raw transcript) | `ThemeAssignment {themes[{label, confidence 0–1, evidence_ids[]}], topics[{name, confidence}]}` stored **inside** `source_analysis.data.themes` | artifact (same version) + `source_video_topics` rows for topics that match an existing `Topic` slug; **new topic names are only stored as proposals** (creating `Topic` rows is a user action — Decision pending) | evidence ids must exist; confidence in range | `source_topics@v1` + analysis hash | as above |
| S4 | **Narrative opportunities** (AI, strongest route) | `SourceAnalysis` (structured, **not** the transcript) | `NarrativeOpportunitySet {opportunities[{id, working_title, premise, central_question, subject, conflict, stakes, key_event_ids[], key_fact_ids[], turning_point_ids[], entity_ids[], tone_hint?, estimated_story_minutes (AI estimate, labelled), independence_note}], none_found_reason?}` | artifact `narrative_opportunity_set`, dependency on the `source_analysis` version | **empty list is valid** (with `none_found_reason`); ids must exist; code computes pairwise Jaccard overlap of referenced event ids and flags `overlaps_with` above a configurable threshold; code rejects an output whose opportunities are contiguous equal time slices (guard against time-splitting) | `narrative_opportunities@v1` + analysis `input_hash` | as above |

**Originality/grounding note:** every fact/event carries `refs`; nothing in P3 judges originality or similarity (that is P4 validation and P12). No legal claims are made or implied.

**Prompt-injection handling:** transcript text is untrusted data. Prompts wrap it in a fixed delimiter block and instruct the model to treat it as data only; the gateway sends it as user content, never in `system`; outputs are accepted **only** via the Pydantic schema (unknown fields rejected, length-bounded, no URLs/tool calls interpreted); S4 never sees raw transcript text; control characters are stripped before windowing. An adversarial fixture ("ignore previous instructions…") is part of the tests; passing it means the output still validates and contains no instruction-following artefacts — it is not a security guarantee ([threat model](../docs/security/threat-model.md)).

**Artifact `input_hash`** for `source_analysis` = hash(transcript content fingerprint, windowing parameters, prompt names+versions of S1–S3, pipeline version). The **model identity is recorded in `meta` but excluded from `input_hash`** (changing model does not mark analysis stale; the user can force a re-run) — see Decision points. For `narrative_opportunity_set` = hash(analysis artifact id + its `input_hash`, prompt version, overlap threshold).

## Database

- NEW table `source_video_topics` (`source_video_id` FK CASCADE, `topic_id` FK CASCADE, `confidence` Float, `artifact_id` FK→artifacts SET NULL; PK `(source_video_id, topic_id)`), in the P3 migration. `Topic` itself unchanged.
- Artifacts reuse P2 tables (`source_video_id` owner, `project_id` NULL). No change to `transcripts`/`transcript_chunks`.
- Index: `artifacts (source_video_id, kind) WHERE is_current`.

## API

| Endpoint | Method | Purpose / contract |
| --- | --- | --- |
| `/api/v1/sources/{id}/analyze` | POST | Body `{force?: bool}`. Validates source exists (404) and has a **ready, current transcript** (409 otherwise). Run key: `source.analyze:<source_id>:<transcript fingerprint>:<pipeline_version>[:force-<nonce>]`. Returns `202 {run_id, reused}`; if an identical run succeeded, returns it with `reused:true` (idempotent) |
| `/api/v1/sources/{id}/analysis` | GET | Current `source_analysis` artifact (`?version=`); 404 if none |
| `/api/v1/sources/{id}/opportunities` | GET | Current `narrative_opportunity_set`; 404 if none |
| `/api/v1/sources/{id}/topics` | GET | Topic links with confidence and proposed (unmatched) topics |
| `/api/v1/artifacts/{id}/versions` | POST | (P2) **edit**: user changes facts/events/themes/opportunities ⇒ new version, `origin=user_edit`; downstream opportunity set becomes stale per [versioning](versioning-and-invalidation.md) and is regenerated by re-running `analyze` with a stage selector or by P3-T8 |
| `/api/v1/sources/{id}/analyze` with `{stage:"opportunities"}` | POST | Optional body field to re-run S4 only (uses the current analysis); 409 if no analysis |

Errors: 404, 409 (no ready transcript / invalid state), 422 (validation), provider failures surface as the run's `error.code`, not as HTTP 5xx.

## Frontend

Source detail route **NEW** `apps/web/src/app/sources/videos/[id]/page.tsx` (P1 may already provide an Overview/transcript tab — extend, do not duplicate); list page `sources/videos/page.tsx` MODIFY to link rows. **Understanding tab** components (**NEW**, `apps/web/src/components/understanding/`): `AnalyzeButton` (POST, then `RunStatus` polling), `FactsTable` and `EventsTimeline` (each row shows grounding refs → click shows the chunk text + timestamp), `EntitiesList`, `ThemesList` (with confidence and linked/proposed topics), `OpportunityCards` (premise, central question, conflict, grounding, overlap flags, "none found" explanation), `ItemEditDialog` (edit/delete an item ⇒ POST new version), `VersionSelect`, `CacheBadge` ("cached — no cost" when all calls in the run were cache hits), `CostBadge` (tokens + estimate from the usage endpoint, "unpriced" when NULL). State: server state via TanStack Query keyed by API path; selected tab in the URL; no new Zustand state. Empty/loading/error states reuse `states.tsx`. A banner explains that opportunities are inputs to P4, not selected stories.

## Services/Workflows

`source.analyze` workflow steps (progress written after each): `prepare` → `extract[window i/n]` → `synthesise` → `themes` → `opportunities` → `finalise`. Each step first checks for an existing artifact/cached calls with the same `input_hash` and skips (resumable by re-execution). Downstream invalidation: a new `source_analysis` version leaves the previous `narrative_opportunity_set` marked stale by hash comparison (no cascade writes). Approval gate: **none** in P3 (analysis is editable, not gated); the human gate is P4.

## AI

Roles and routing: S1–S2/S4 `analysis` (S1 is the high-volume stage — a cheaper/local candidate is plausible **if the benchmark shows adequate JSON validity**; unverified), S3 `classification`. Prompt strategy, structured output and repair per P2 gateway; schemas as above; `temperature` low for extraction, moderate for S4 (route-level). Cost levers: one pass if the transcript fits; map-reduce only when it does not; S3/S4 consume the compact analysis, not the transcript; everything cached.

**AI decides:** which statements are facts/events, relations between them, themes, which arcs are story-worthy, working titles/premises. **Code decides:** windows, ids, ordering, timestamps/refs resolution, dedupe, overlap flags, validation, persistence, versions, cache keys, run state.

## Storage/media

None (no files). Transcript raw files (P1, D6) are read only through `LocalStorage` if S0 needs them; S0 uses DB chunks.

## Testing

- **Unit:** windowing (coverage, sizes, determinism); id assignment/dedupe/ordering; ref resolution; overlap Jaccard and the anti-time-slicing check; topic slug matching; schema bounds.
- **Golden fixtures** (`apps/api/tests/fixtures/ai/<prompt>/…`, human-reviewed recorded outputs): each stage's output passes validation; a corrupted fixture fails with the expected error.
- **Workflow (fake provider):** full `source.analyze` on a small sample; second run ⇒ 0 provider calls and `reused:true`; failure injected in window 2 ⇒ `failed` at that step ⇒ retry resumes at window 2 without repeating window 1; edit creates v2 and the opportunity set reads as stale; "none found" path persists an empty set.
- **Adversarial fixture:** injection text inside a transcript does not break schema validation and does not alter ids/refs.
- **API:** 404/409/422, idempotent analyze, versions endpoint.
- **Frontend:** Vitest for components with fixture data (grounding link, none-found state, cached/unpriced badges). **Playwright** (`ENABLE_FAKE_LLM=true`, seeded source+transcript via API): add source → Analyze → see facts/opportunities → edit a fact → see new version; second Analyze shows "cached".
- **Not claimed:** quality of real-model outputs. A user-run, recorded manual evaluation on 2–3 real sources is part of P3's closing checklist ([AI evaluation](../docs/testing/ai-evaluation.md)).

## Observability

Per-stage run `progress` (`{step, done, total}`), `llm.call` events per window with `source_id`, `task`, tokens, cache flag; validator rejections logged with counts (not content). Usage endpoint shows the cost of an analysis. A `run.finished` event includes `{windows, cache_hits, repairs}`.

## Failure handling & idempotency

Window-level retry via gateway; a window that cannot be validated after repair fails the run at that step and is resumable; partial results are not exposed as `source_analysis` (artifact is created only after S2–S3 validate). Re-running with unchanged inputs is a pure cache replay. Editing never mutates a version in place. Provider outage ⇒ route fallback ⇒ otherwise run `failed` with `error_code`, source status unaffected.

## Tasks

| ID | Task | Verified by |
| --- | --- | --- |
| P3-T1 | Schemas + kind registration + `source_video_topics` migration | schema/constraint tests |
| P3-T2 | `windows.py` (S0) with route-derived budget | windowing unit tests |
| P3-T3 | Prompts `source_extraction@v1`, `source_synthesis@v1`, `source_topics@v1`, `narrative_opportunities@v1` + lock entries | lock test; fixtures validate |
| P3-T4 | `stages.py` S1–S4 + code validators/mergers | stage unit tests with fixtures |
| P3-T5 | `workflow.py` `source.analyze` + registry + idempotent key | workflow tests |
| P3-T6 | Understanding API routes | API tests |
| P3-T7 | Topic matching + `GET /sources/{id}/topics` | unit + API tests |
| P3-T8 | Stage re-run (`{stage:"opportunities"}`) and stale display hook | workflow test |
| P3-T9 | Frontend Understanding tab + Vitest + Playwright | UI tests |
| P3-T10 | Manual real-provider evaluation checklist on 2–3 sources; record outcome in the PR/notes (not as a pass/fail gate) | user-run |
| P3-T11 | Docs/status updates | review |

## Acceptance criteria (Checkpoint C)

1. For a source with a ready transcript, `POST /sources/{id}/analyze` yields a `succeeded` run and a current `source_analysis` whose every fact/event/relation `refs` resolve to existing chunks, with code-assigned ids and timestamps.
2. A `narrative_opportunity_set` exists with ≥0 opportunities; a zero-opportunity result is accepted with a stated reason; each opportunity references existing event/fact ids; none are contiguous equal time slices.
3. Re-running without `force` makes **zero** provider calls (`reused:true` or all `cache_hit`); with `force` it makes new calls.
4. Failure in window k resumes at window k on retry; earlier windows are not re-called.
5. Editing a fact creates version 2 (`origin=user_edit`), keeps v1 immutable, and the opportunity set is reported stale by the versioning mechanism.
6. Topics: matched topics are linked with confidence; unmatched are listed as proposals; no `Topic` rows are created implicitly.
7. The adversarial-transcript fixture passes (schema-valid output, no cross-contamination of ids/refs).
8. UI: the Understanding tab shows facts/events with grounding, themes, opportunities, version select, edit, re-run, cached and cost badges; Playwright flow passes against the fake provider.
9. `make lint`, `make test` (DB), `make e2e` green; docs updated.

## Deliverables

Understanding package, four prompts (v1), `source.analyze` workflow, source-scoped API, `source_video_topics`, Understanding UI, fixtures, tests, docs.

## Dependencies

Depends on P1, P2. Required by P4 (candidates consume `narrative_opportunity_set`), P5 (grounding), P11 (multi-source). Independent of P6–P8.

## Do NOT

- Do not feed the whole transcript into one prompt "to save effort"; do not let S4 see raw transcript text.
- Do not accept timestamps or ids from the model; do not create `Topic` rows implicitly.
- Do not select a story here (P4 owns the approval gate) or generate scripts/prompts for images.
- Do not slice by time; do not treat "no opportunity" as an error.
- Do not call an embedding model (embeddings are P11).

## Docs to update at phase end

[research and intelligence](../docs/domains/research-and-intelligence.md), [source library](../docs/domains/source-library.md) (analysis as a source property), [topic and collection system](../docs/domains/topic-and-collection-system.md), [story generation pipeline](../docs/ai/story-generation-pipeline.md), [research workflow](../docs/workflows/research-workflow.md), [story data model](../docs/data/story-data-model.md), [API](../docs/api/README.md), [frontend routing](../docs/frontend/routing.md), [status](../docs/reference/status.md) (add/adjust rows), [changelog](../docs/reference/changelog.md).

---

## Decision points (this file)

1. **Cache key superset (disagrees mildly with D2):** this plan keys the cache on `(task, provider, model, prompt_name, prompt_version, request_hash)` instead of `(task, model, prompt_version, request_hash)`. Reason: prevents cross-prompt and cross-provider collisions. Low risk; confirm.
2. **Model excluded from artifact `input_hash`** (changing model does not stale analysis; recorded in `meta`). Alternative: include it and accept more staleness. Decide before P3-T5.
3. **Topic creation policy:** proposals only (this plan) vs auto-create. `Topic` has no status column; a `status`/`origin` column would be a schema change — deferred.
4. **`cancel_requested` cooperative cancel** is included; skipping cancel in the MVP is acceptable if time-boxed.
5. **`llm_calls.response_text` retention** (keep vs prune) — default keep; revisit in P10.
6. **`artifacts` as a generic table (D3)** is assumed; if P3 experience shows heavy querying inside `data`, split into typed tables after P5 (master decision #5).
7. **Windowing heuristic** uses chars/4 as a token estimate; replace with a real tokenizer only if a chosen provider requires it.
8. **Where `understanding/` lives:** placed under `app/intelligence/` (research domain); alternative is a new `app/research/` package. Pick once before P3-T1.

## Assumptions

P1 provides a current transcript, chunks and a transcript fingerprint and (per `02-source-library.md`) creates `workflow_runs` + `RunService`; P2 extends them. If P1's final shape differs from the columns above, P2-T4 adapts to the code rather than duplicating the table. `01-foundation.md` closes KI-4/6/8/11/19 before P2; if it also closes KI-2/KI-3, those tasks shrink to verification. No local model is assumed to exist or to be fast enough; cloud/free-tier routes are configuration. Python 3.12 stdlib (`tomllib`, `string.Template`) is used for prompts to avoid new dependencies.
