# AI Ingest

`v1`

AI Ingest is a small script that pulls AI/ML updates from a handful of good sources, ranks what looks worth reading, and emails you a clean digest.

I built it to be simple to run and easy to tweak:

- sources live in [`sources.toml`](./sources.toml)
- model choice is up to you
- output is written to markdown, HTML, and JSON
- email delivery works with normal SMTP, including Gmail

## What It Pulls From

By default it checks:

- Hugging Face
- Latent Space
- Simon Willison
- Eugene Yan
- Chip Huyen
- HN Who's Hiring for AI/ML roles

The fetch step is balanced across sources so one feed does not crowd out the rest.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

Then fill in your model and email settings in `.env`.

The main one is:

```bash
INGEST_MODEL=openai/<model>
```

You can also use Anthropic, xAI, Vertex, OpenRouter, or an OpenAI-compatible endpoint.

If you want email delivery, set:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `INGEST_TO`

`INGEST_TOP_N` controls how many items end up in the digest. Default is `10`.

## Run It

Preview a run without sending email:

```bash
python -m ai_ingest --dry-run --print
```

Run it for real:

```bash
python -m ai_ingest
```

Files land here:

- `out/latest.md`
- `out/latest.html`
- `out/latest.json`

Seen items are tracked in `state/seen_ids.json`.

## Why This Version Exists

The repo that inspired this one was solid, but I wanted something a little more flexible:

- batched ranking instead of one model call per article
- easier provider swapping
- normal SMTP instead of a Gmail-only path
- a shorter setup surface

## Test

```bash
pytest
```
