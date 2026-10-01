# Quality Gates

> What must pass before a change is considered good, and what enforces it today.

## Status

Partially implemented. Gates are local commands; **there is no CI** ([KI-10](../reference/status.md#known-issues-and-limitations)), so nothing blocks a merge automatically.

## `make lint`

1. `ruff check app tests` (rules E,F,I,UP,B,SIM) and `ruff format --check`.
2. `pyright` (strict, relaxed unknown-type reports) over `app` and `tests`.
3. Web: `eslint`, `tsc --noEmit`. Video: `tsc --noEmit`.

Prettier check for the web app is separate: `pnpm --filter @storyweaver/web format:check` (not in `make lint`).

## `make test`

pytest, Vitest for web and video (counts and the skip behavior without a database: [testing strategy](testing-strategy.md#layers)). `make e2e` is separate and needs the stack running. `TEST_DATABASE_URL` must be a disposable database ([KI-19](../reference/status.md#known-issues-and-limitations)).

## Manual gates

`alembic check` after model changes; `next build` before releasing UI changes; `make render-sample` after touching `packages/video`; `git status` clean of `.env`/media.

## Not enforced

Coverage thresholds, dependency audit, secret scanning, link-checking of `docs/`, schema/contract drift, performance budgets, CI. Adding CI is Decision pending.

## Manual documentation check (not automated)

No link checker exists in the repository. This throw-away procedure checks relative links, heading anchors and the title/purpose/status header of every document; run it from the repository root and treat any output as a defect. It is guidance, not a gate:

```bash
python3 - <<'PY'
import re, pathlib
root = pathlib.Path("docs")
slug = lambda h: re.sub(r"[^\w\- ]", "", re.sub(r"[`*\[\]]", "", h.strip().lower())).replace(" ", "-")
anchors = {}
def heads(p):
    if p not in anchors:
        anchors[p] = {slug(l.lstrip("#")) for l in p.read_text().splitlines() if re.match(r"#{1,6} ", l)}
    return anchors[p]
for p in sorted(root.rglob("*.md")):
    t = p.read_text(); lines = t.splitlines()
    if not lines[0].startswith("# ") or "## Status" not in t or not any(l.startswith(">") for l in lines[:6]):
        print("HEADER", p)
    for m in re.finditer(r"\]\(([^)#\s]*)(#[^)]*)?\)", t):
        link, frag = m[1], (m[2] or "")[1:]
        if re.match(r"(https?:|mailto:)", link): continue
        tgt = (p.parent / link).resolve() if link else p.resolve()
        if not tgt.exists(): print("BROKEN", p, link)
        elif frag and tgt.suffix == ".md" and frag not in heads(tgt): print("ANCHOR", p, link + "#" + frag)
PY
```

Related: [testing strategy](testing-strategy.md), [coding standards](../development/coding-standards.md).
