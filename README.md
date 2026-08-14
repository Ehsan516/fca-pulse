# FCA Pulse

An automated regulatory intelligence tracker for UK financial firms. FCA Pulse polls the FCA and PRA/Bank of England publication feeds daily, classifies each new item with Claude into a structured schema (regulation area, affected firm types, key deadlines, impact level), archives everything, and publishes a searchable, filterable static web digest — no server, no database service, near-zero cost.

See [`fca-reg-tracker-requirements.md`](fca-reg-tracker-requirements.md) for the full requirements brief. This build covers the core scope: ingestion (FR1), classification (FR2), storage/archive (FR3), and the web digest (FR4). The weekly digest/RSS (FR5) and FCA Handbook diff detection (FR6) are deferred follow-ups, not yet implemented.

## How it works

1. **Ingest** (`fca_pulse.ingest`) — polls the feeds in [`config/feeds.yaml`](config/feeds.yaml), dedupes by a hash of each item's URL, and fetches the full article text (respecting `robots.txt` and a per-domain rate limit).
2. **Classify** (`fca_pulse.classify`) — sends each new item to Claude with a version-controlled prompt ([`config/prompts/classify.md`](config/prompts/classify.md)) using tool-use for structured output, validated against the controlled vocabularies in [`config/vocab.yaml`](config/vocab.yaml). Items that fail validation twice are stored flagged `classification_failed`, never dropped.
3. **Store** (`fca_pulse.storage`) — an append-only SQLite archive at `data/archive.db`, committed back into the repo after each run so it survives GitHub Actions' ephemeral runners.
4. **Publish** (`fca_pulse.site`) — renders a static site into `docs/`: a reverse-chronological digest with client-side filter/search, and an "Upcoming Deadlines" view (next 90 days, soonest first).

A daily GitHub Actions workflow ([`.github/workflows/pipeline.yml`](.github/workflows/pipeline.yml)) runs the whole pipeline, commits the updated archive and site, and pushes to `main`. GitHub Pages serves the site straight from `main`'s `/docs` folder.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install -e .
```

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`, or export it directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Run the full pipeline (ingest, classify, store, build site):

```bash
python -m fca_pulse.pipeline
```

Useful flags:

- `--skip-classification` — ingest and build the site without calling Claude (items are stored flagged `classification_failed`). Good for smoke-testing without spending API credits.
- `--site-only` — regenerate `docs/` from the existing archive without re-ingesting.
- `--db PATH` / `--site-dir PATH` — override the default `data/archive.db` / `docs/` locations.

Open `docs/index.html` in a browser to view the generated digest, or serve it locally:

```bash
python -m http.server -d docs 8000
```

## Tests

```bash
pytest
```

Covers dedup identity, classification schema validation (including controlled-vocabulary and ambiguous-date rejection), archive idempotency, and deadline windowing/sorting.

## Enabling GitHub Pages

In the repo's **Settings → Pages**, set the source to the `main` branch, `/docs` folder. The first successful run of the daily workflow (or a manual "Run workflow" dispatch) will populate `docs/`.

## GitHub Actions secret

Add your Anthropic API key as a repository secret named `ANTHROPIC_API_KEY` (**Settings → Secrets and variables → Actions**) so the scheduled workflow can classify new items.
