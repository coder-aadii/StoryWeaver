# P0 — Foundation Hardening and Defect Triage

> Make the existing foundation trustworthy before building product on it: close the defects that would corrupt later work, fix the render-asset contract, and establish the shared engineering conventions every later phase uses.

## Status

Planned. Phase **P0** of [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md); delivers **Checkpoint A**. Current state of every item below is taken from the code and from [`docs/reference/status.md`](../docs/reference/status.md#known-issues-and-limitations); each task re-verifies it before changing anything (the known-issue claims were audited against the code, but the code may have moved).

## 1. Goal

A fresh clone passes lint and tests with a real database, nothing writes to the wrong place, provider and API failures are handled and logged correctly, the Python↔TypeScript timeline contract is test-enforced, and the **render asset path** (how a generated image or WAV reaches the Remotion renderer — [KI-17](../docs/reference/status.md#known-issues-and-limitations)) is decided and proven with a fixture render. No product feature is added.

## 2. Why now

- These defects are cheap now and expensive later: once real data, real provider calls and Timeline consumers exist, each fix needs migrations or data repair.
- Three of them *change what later phases must build*: KI-3 (every AI stage depends on provider error semantics), KI-7/KI-17 (Timeline v2 and the render pipeline), KI-1/KI-9 (where files live).
- The test-database guard (KI-19) must exist before the database holds anything worth losing.

## 3. Prerequisites

None. Environment: `uv`, pnpm, Docker-free Postgres helper (`make db-up-nodocker`) or Docker; `TEST_DATABASE_URL` pointing at a **disposable** database.

## 4. Known-issue triage (all 26)

Classification: **B** = blocking prerequisite (fix in P0); **S** = should fix before the named milestone; **A** = fix alongside the named phase; **L** = later hardening. "Task" is the P0 task that fixes it. Nothing here is fixed by this plan; the fixes are future work. Issue text lives in [status.md](../docs/reference/status.md#known-issues-and-limitations).

| KI | Issue (short) | Class | Phase / Task | Reason |
| --- | --- | --- | --- | --- |
| 1 | Empty `STORAGE_ROOT` → `.` | **B** | P0-T2 | P1 writes raw transcripts via `LocalStorage`; a wrong root silently pollutes the source tree |
| 2 | Redaction masks `output_tokens` | **S** (before P2) | P0-T3 | Cost/usage tracking (P2) needs token fields in logs; cheap to do first |
| 3 | Provider non-HTTP errors unwrapped | **B** | P0-T4 | Every AI stage depends on one failure model |
| 4 | PATCH null → 409; no update length limits → 500 | **S** (before P1 UI) | P0-T5 | P1 adds editing UI against these endpoints |
| 5 | `/health/ready` silent; no connect timeout | A | P0-T5 | Small; improves every later debugging session |
| 6 | Embedding dimension setting unlinked | **S** (before P11) | P0-T2 (guard test only) | Guard is a one-line test now; embeddings are P11 |
| 7 | zod ↔ Pydantic drift | **B** | P0-T6 | Must hold before Timeline v2 |
| 8 | `StoryWeaverError` not mapped to HTTP | **S** (before P1 endpoints) | P0-T5 | New endpoints will raise these |
| 9 | `LocalStorage`/`LocalRunner` unused by routes | A | P1 (storage), P2 (runner) | Wired by their first real consumer, not in isolation |
| 10 | No CI | L | P10 (D15; earlier if cheap) | Local checks suffice for a single developer until MVP |
| 11 | Cached engine in tests | **S** | P0-T1 | Order-dependent tests become likely as DB tests grow |
| 12 | Create endpoints accept any URL | **B** | P0-T5 (schema validation); P1 later replaces the raw create routes with a validating service | P1 fetches from these URLs |
| 13 | Transcript `version` unsettable → 409 | A | P1 | Resolved by a service, not the API payload (D6) |
| 14 | Uploaded transcript not representable | A | P1 | Migration D5 |
| 15 | `extract()` metadata only | A | P1 | The core of P1's YouTube path |
| 16 | 2–7 s estimate truncates long narration | A | P7 | Replaced by measured-audio resolution policy |
| 17 | Assets not servable / not resolvable by renderer | **B** (decision) | P0-T7 decides; P6 (preview route) and P8 implement | Fixes the Timeline v2 contract |
| 18 | ComfyUI stub selected when URL set | A | P6 | Replaced by the real adapter/selection logic |
| 19 | Destructive `TEST_DATABASE_URL`, no guard | **B** | P0-T1 | Protects real data |
| 20 | Dev servers bind beyond localhost | A | P0-T8 | One-line Makefile/script change (D14) |
| 21 | `NEXT_PUBLIC_API_URL` env location | A | P0-T8 | Add `apps/web/.env.example`/docs |
| 22 | No storage for used ideas/candidates/analysis/dependencies | A | P1 (source usage), P2 (artifacts), P4 (candidates) | Addressed by the tables that need them |
| 23 | No thumbnail/sync cursor | A | P1 (thumbnail), P11 (cursor) | |
| 24 | Channel id from URL fragment | A | P11 | Channel import is P11 |
| 25 | Google Fonts needed at build | L | P10 | Cosmetic offline concern |
| 26 | Root README / `.env.example` out of date | A | P0-T2, P0-T9 | These files *are* editable during execution; this planning task did not touch them |

## 5. Shared engineering conventions (apply to all later phases)

- **Layering:** routes (thin) → `app/<domain>/service.py` (NEW per domain; all logic, takes a `Session`) → models. The generic `crud_router` stays for plain resources; any resource with logic gets an explicit router in `app/api/v1/<resource>.py` (NEW) registered in `api/v1/router.py` (MODIFY).
- **Error mapping:** one exception handler (P0-T5, MODIFY `app/main.py`) maps `StoryWeaverError` subclasses → HTTP: `InvalidSourceError`→422, `UnsafePathError`→400, `ProviderNotConfiguredError`→409 (with a stable error `code`), `ProviderError`→502, size-cap → 413. Response shape `{"detail": str, "code": str}` so the UI can show messages ([docs/api/errors.md](../docs/api/errors.md)).
- **Migrations:** one Alembic revision per task group, named `NNNN_<phase>_<what>`; run `upgrade → downgrade base → upgrade` and `alembic check` in a test (NEW `tests/test_migrations.py`); keep constraints named via the existing naming convention.
- **Idempotency:** every workflow kind has a row in the idempotency table ([retry-and-recovery](../docs/workflows/retry-and-recovery.md#idempotency-keys)); services accept/derive the key and are safe to call twice.
- **Tests:** shared factories (NEW `tests/factories.py`) and fixture files (NEW `apps/api/tests/fixtures/`: yt-dlp info JSON, caption files, recorded provider JSON, tiny PNG/WAV). Provider/network access in tests only through `httpx.MockTransport` or fakes.
- **Logging fields:** `workflow_id`, `project_id`, `source_id`, `scene_id`, `provider`, `model`, `duration`, `status`, `error` — via `get_logger(**ctx)`; never log prompts/transcript bodies at INFO.
- **Task IDs and commits:** `Pn-Tm`; commit only when the user asks.

## 6. Tasks

### P0-T1 — Test safety and isolation (KI-19, KI-11)
- **MODIFY** `apps/api/tests/conftest.py`: before `downgrade base`, refuse to run unless the database name ends in `_test` (or `STORYWEAVER_ALLOW_DESTRUCTIVE_TESTS=1`) **and** `TEST_DATABASE_URL != DATABASE_URL`; skip with a clear message otherwise.
- **MODIFY** `conftest.py`: clear `get_engine`/`get_sessionmaker` caches (`cache_clear()`) when the engine fixture rebinds settings; make the API-with-DB tests use the test engine explicitly.
- **NEW** `apps/api/tests/test_migrations.py`: up → down → up, `alembic check` clean.
- **Acceptance:** pointing `TEST_DATABASE_URL` at a database not ending in `_test` aborts before any DDL (test asserts); running the DB tests in reverse order passes (`pytest -p no:randomly` and `--reverse` via a small plugin or `-k` ordering check); migration test passes.

### P0-T2 — Configuration correctness (KI-1, KI-6, KI-26 part)
- **MODIFY** `apps/api/app/core/config.py`: field validator treats an empty `storage_root` as unset (default `<repo>/data`); resolve to absolute; fail fast if it resolves inside `apps/` source dirs? (decision: simply require absolute-resolved and writable).
- **MODIFY** `.env.example`: remove or comment `STORAGE_ROOT=`; add `ENVIRONMENT`, `LOG_LEVEL`, `MAX_UPLOAD_BYTES`, `CORS_ORIGINS` (commented, with defaults).
- **NEW** test: `Settings(storage_root="")` resolves to `<repo>/data`; **NEW** test asserting `Settings().embedding_dimensions == EMBEDDING_DIM` (documented as a guard for P11, [D8](IMPLEMENTATION_PLAN.md#7-technical-decisions-recommended-defaults)).
- **Acceptance:** `cp .env.example .env` then `get_storage().root` equals `<repo>/data`; tests above pass.

### P0-T3 — Log redaction fix (KI-2)
- **MODIFY** `apps/api/app/core/logging.py`: replace substring matching with a redaction rule over *exact secret-style key names and suffixes* (`api_key`, `apikey`, `authorization`, `password`, `secret`, `*_token` **excluding** `*_tokens`, `credential(s)`), plus a value-pattern scrub for obvious key formats (e.g. `sk-…`, long base64-ish bearer strings) applied to string values and exception messages logged by the runner.
- **Acceptance:** `info("llm.generated", output_tokens=5, max_tokens=9)` logs the numbers; `info("x", api_key="abc")`, `authorization="Bearer …"` and an exception message containing a key-shaped string are masked (unit tests, including a table of true-positive and false-positive keys).

### P0-T4 — Provider error model and contract tests (KI-3)
- **MODIFY** `intelligence/providers/base.py`: define `ProviderResponseError(ProviderError)`; wrap `KeyError/IndexError/TypeError/json.JSONDecodeError` raised while parsing a response inside `generate`; make timeouts configurable (`Settings.llm_timeout_seconds`, default current 120 s); `generate_structured` retries on `ProviderResponseError` as well as validation errors.
- **MODIFY** each adapter (`ollama.py`, `google.py`, `openai_compatible.py`, `claude_compatible.py`): no behavior change except surfacing empty/blocked responses (e.g. Google with no `candidates`) as `ProviderResponseError` with a safe message.
- **NEW** `tests/test_provider_contract.py`: a parametrized suite run against every LLM adapter and both embedding adapters using `httpx.MockTransport`: correct request path/headers/body, success parse, HTTP 4xx/5xx → `ProviderError`, malformed 200 → `ProviderResponseError`, timeout → `ProviderError`, key never present in raised message or logs.
- **Acceptance:** suite green for all adapters (this also closes the "only Ollama is tested" gap — recorded honestly as *mock-tested*, still not live); `status.md` provider row updated.

### P0-T5 — API hardening (KI-4, KI-5, KI-8, KI-12)
- **MODIFY** `schemas/resources.py`: add `max_length` to every `*Update` string; `ConfigDict(extra="forbid")` retained; forbid `null` for NOT NULL fields (use `Field(default=None)` plus a validator rejecting explicit `None` where the column is NOT NULL, or per-field `StrictStr` with `exclude_unset` semantics) → 422 instead of 409/500.
- **MODIFY** `api/crud.py`: map `DataError` → 422, keep `IntegrityError` → 409 with a code distinguishing unique vs FK where determinable.
- **MODIFY** `main.py`: exception handler per §5.
- **MODIFY** `schemas/resources.py` (`ChannelCreate`, `SourceVideoCreate`): when `platform == "youtube"`, validate `url` with `classify_youtube_url` (kind must match: video vs channel) → 422.
- **MODIFY** `api/v1/health.py` + `db/session.py`: log the readiness exception (type + sanitized message), set `connect_args={"connect_timeout": 3}`, include `detail` field per failing check.
- **Acceptance:** tests: PATCH `{"title": null}` → 422; 10k-char title → 422; create source with `https://evil.example/x` and platform youtube → 422; readiness with an unreachable DB URL returns 503 within ~3 s and logs one line; a route raising `ProviderNotConfiguredError` returns 409 with `code`.

### P0-T6 — Python↔zod contract test (KI-7)
- **NEW** `packages/video/src/contract.test.ts` + a generated fixture: `make schemas` also emits a canonical valid/invalid sample set from Pydantic (`scripts/export_schemas.py` MODIFY) into `packages/schemas/`; the Vitest test parses every valid sample with the zod schema and asserts invalid ones fail; a Python test parses the sample timeline with `Timeline`.
- Align known differences (decide and encode): `camera` default, `camera.shot` enum (zod enum matches Python Literal).
- **Acceptance:** changing a field in `scene.py` without updating `types.ts` fails `make test`.

### P0-T7 — Render asset-path spike and decision (KI-17, D12)
- **NEW** (throwaway-quality but committed as a script) `packages/video/scripts/spike-assets.ts` or a documented manual procedure: a fixture project dir with `images/a.png`, `audio/a.wav`; render via `remotion render … --public-dir <dir>` with a composition variant that uses `staticFile(scene.image_src)` and `<Audio src={staticFile(...)}>`; assert the MP4 decodes and a sampled frame contains the image (compare to the fixture within tolerance) and that audio duration ≈ WAV duration.
- Also measure render wall-clock for a 60 s fixture on the dev machine (record the number; no performance promise).
- **Deliverable:** an ADR (`docs/decisions/ADR-009-render-asset-resolution.md`, written when executed) recording the chosen approach (expected D12) and the **Timeline v2 field proposal** consumed by [P8](06-timeline-render-qa.md); fixture files under `packages/video/sample/`.
- **Acceptance:** fixture render passes the assertions above; ADR written; D12 confirmed or replaced.

### P0-T8 — Local-only binding and web env (KI-20, KI-21)
- **MODIFY** `Makefile`: `dev-api` uses `--host 127.0.0.1`; `apps/web/package.json` `dev`/`start` use `-H 127.0.0.1`.
- **NEW** `apps/web/.env.example` with `NEXT_PUBLIC_API_URL`; remove it from the root `.env.example` comment or point to the web file.
- **Acceptance:** `ss -ltn` shows both servers only on `127.0.0.1`; fresh-clone setup instructions in `docs/development/setup.md` work verbatim.

### P0-T9 — Docs and status reconciliation
- Update `docs/reference/status.md` Known issues (mark closed items with the commit/phase, move closed text to the changelog), the provider/test rows, and any docs that cite closed KIs; keep KI ids stable (never renumber).
- **Acceptance:** no doc still describes a closed defect as current; `grep -R "KI-<closed>" docs` points only at history entries.

## 7. Backend / Database / API / Frontend / AI / Storage

- **Backend:** as per tasks above. **Database:** no schema change in P0 (migration test only). **API:** behavior fixes only (422/409/502 mapping; readiness). **Frontend:** none except env example. **AI:** none (provider error model only). **Storage/media:** none (storage root fix; spike fixtures).

## 8. Testing

Unit + contract + API + migration tests as listed; one fixture render (spike) — gated behind a `render` pytest/Vitest marker or a manual script so default `make test` stays fast. The existing counts/commands are canonical in [testing strategy](../docs/testing/testing-strategy.md); update them there at the end.

## 9. Observability, failure handling, idempotency

Readiness failures and provider failures become logged, typed, user-visible errors. No workflows exist yet, so idempotency is not applicable in P0 beyond the migration up/down/up test.

## 10. Acceptance criteria (Checkpoint A)

1. `make lint` clean; `make test` green with `TEST_DATABASE_URL` set to a `_test` database; DB tests demonstrably ran (not skipped).
2. Every task acceptance above passes.
3. A fixture render with a real image and WAV produces an MP4 verified by frame sample and audio duration; D12 decision recorded.
4. `status.md` known-issues table reflects reality; KI-1, 2, 3, 4, 5, 7, 8, 11, 12, 19, 20, 21 closed (others reassigned as in §4).

## 11. Deliverables

Hardened config/logging/provider/API behavior; migration and contract tests; shared test factories/fixtures; ADR-009 and a Timeline v2 proposal; reconciled docs.

## 12. Dependencies

Blocks P1 (KI-1, 12, 4, 8, 19), P2 (KI-2, 3), P8 (KI-7, KI-17 decision). Independent of the AI phases otherwise.

## 13. Do NOT

- Do not start the job table, artifacts, prompts or any AI stage here.
- Do not change the database schema in P0.
- Do not "fix" things not in the triage; add new findings to `status.md` instead.
- Do not make ComfyUI, Ollama, Docker or a GPU a requirement.

## 14. Decision points

- Redaction strategy: exact-name + value-pattern (recommended) vs allowlist logging. 
- Whether the `_test` suffix guard should be overridable (recommended: explicit env var only).
- D12 confirmation after the spike.
