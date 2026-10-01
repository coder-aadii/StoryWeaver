# Threat Model

> Realistic threats for a local-first tool, with current mitigations and gaps.

## Status

Partially implemented (mitigations); the model itself is a first pass and should be revisited when auth, workflows or remote deployment arrive.

## Assets

Provider API keys; source transcripts and generated scripts (possibly sensitive/licensed); the database; `data/` media; the user's machine.

## Trust boundaries

Browser ↔ API (unauthenticated, localhost); API ↔ providers (network, may be cloud); API ↔ yt-dlp/YouTube (untrusted remote content); API ↔ filesystem; model output ↔ everything.

## Threats

| # | Threat | Current mitigation | Gap / next step |
| --- | --- | --- | --- |
| 1 | **API or web UI exposed to a network** (anyone can read/delete data, trigger paid provider calls) | uvicorn default binds `127.0.0.1`; CORS origins; docs say localhost only | No auth; Decision pending before any exposure. `next dev` binds beyond localhost (prints a LAN URL), so the UI is reachable from the network unless started with `-H 127.0.0.1` ([KI-20](../reference/status.md#known-issues-and-limitations)) |
| 2 | **SSRF / malicious URL via ingestion** (yt-dlp fetching internal addresses) | Strict YouTube host allow-list before extraction | URL validation runs only inside the extractor; `POST /sources` and `/channels` store any string ([KI-12](../reference/status.md#known-issues-and-limitations)), so re-validate before any fetch; yt-dlp redirects are its own behaviour |
| 3 | **Path traversal** via filenames/keys | `LocalStorage.path_for`, `sanitize_filename`, tests | Upload endpoints not built; symlink/TOCTOU edge cases accepted locally |
| 4 | **Prompt injection from transcripts/web sources** (steer story, exfiltrate via output, abuse tools) | None needed yet (no prompts); design rules in [provider security](provider-security.md) | Delimit untrusted text, no tool access, schema-validate outputs, human review before publishing |
| 5 | **Secret leakage** (logs, health endpoint, frontend bundle, git) | Redaction, boolean health, `.gitignore`, header-based keys, a manual pattern scan before the initial commit (no pre-commit hook or CI scanner exists) | No automated scanning; key-name-only substring redaction that does not scrub exception text ([KI-2](../reference/status.md#known-issues-and-limitations)) |
| 6 | **Cloud data disclosure** (sources sent to third parties/proxies) | Local-first default (Ollama) | Per-source/per-provider privacy policy: Planned |
| 7 | **Supply chain** (npm/PyPI packages, yt-dlp, Remotion/Chrome downloads, `latest` images) | Lockfiles (`uv.lock`, `pnpm-lock.yaml`); pnpm build scripts allow-listed | No audit, no pinning of Docker `latest`, Remotion downloads Chrome at first render |
| 8 | **Resource exhaustion** (huge uploads, many background jobs, long renders) | Upload cap, 2-worker `LocalRunner`, lazy model loading | No rate limits/quotas; jobs not cancellable |
| 9 | **Malicious media** exploiting FFmpeg/Chrome | None specific | Keep tools updated; sandbox rendering — Deferred until required by the production workflow |
| 10 | **Copyright/misuse of source content** | None technical | Product-policy issue; originality/similarity checks are a goal, **not a guarantee** ([content policy](../product/content-policy-and-source-usage.md)) |
| 11 | **SQL injection** | SQLAlchemy parameterisation | Keep raw SQL out of request paths |
| 12 | **Dependency on unauthenticated health probes calling configured URLs** | URLs are operator config, 2 s timeout | Never derive them from requests |

Overview: [security overview](security-overview.md); architecture: [security architecture](../architecture/security-architecture.md).
