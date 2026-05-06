# AI Ingest

AI Ingest is a small daily digest generator for AI and machine learning news.
It fetches updates from a configurable list of sources, asks an LLM to rank the
useful items, writes Markdown/HTML/JSON output, and can email the digest through
standard SMTP.

It is intentionally plain Python: clone it, add a `.env`, run one command.

## What It Does

- Pulls new AI/ML items from RSS feeds and Hacker News job posts.
- De-duplicates items already seen in previous real runs.
- Balances candidates across sources so one feed does not dominate the digest.
- Uses LiteLLM, so you can use OpenAI, Anthropic, xAI, OpenRouter, Vertex, or an
  OpenAI-compatible endpoint.
- Writes `out/latest.md`, `out/latest.html`, and `out/latest.json`.
- Sends the digest by SMTP when email settings are configured.

## Default Sources

The default `sources.toml` checks:

- Hugging Face
- Latent Space
- Simon Willison
- Eugene Yan
- Chip Huyen
- Hacker News "Who's Hiring" posts that mention AI/ML terms

Edit `sources.toml` to add, remove, or tune sources.

## Requirements

- Python 3.11 or newer
- An LLM API key for the provider you choose
- Optional: an SMTP account if you want email delivery

For Gmail delivery, use a Google account with 2-Step Verification enabled and a
Gmail App Password. Your normal Gmail password usually will not work for SMTP.

## Quick Start

Clone the repo:

```bash
git clone https://github.com/yyzquwu/ai-ingest.git
cd ai-ingest
```

Create a virtual environment and install the package:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

Create your local environment file:

```bash
cp .env.example .env
```

Edit `.env` and set at least one model plus the API key for that provider.

Example with Anthropic:

```bash
INGEST_MODEL=anthropic/claude-sonnet-4-5
ANTHROPIC_API_KEY=sk-ant-...
```

Example with OpenAI:

```bash
INGEST_MODEL=openai/gpt-4.1-mini
OPENAI_API_KEY=sk-...
```

Example with OpenRouter:

```bash
INGEST_MODEL=openrouter/anthropic/claude-sonnet-4.5
OPENROUTER_API_KEY=sk-or-...
```

## Configure Email Delivery

Email is optional. If SMTP settings are blank, AI Ingest still writes digest
files to `out/`, but it skips email delivery.

For Gmail SMTP, add this to `.env`:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USE_STARTTLS=false
SMTP_USERNAME=your.name@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=your.name@gmail.com
INGEST_TO=your.name@gmail.com
```

Notes:

- `SMTP_PORT=465` uses implicit TLS.
- If your SMTP provider requires STARTTLS, use `SMTP_PORT=587` and
  `SMTP_USE_STARTTLS=true`.
- `SMTP_FROM` should usually match `SMTP_USERNAME`.
- `INGEST_TO` can be one recipient address.

## Run It

Preview a digest without sending email or marking items as seen:

```bash
python -u -m ai_ingest --dry-run --print
```

Run it for real:

```bash
python -u -m ai_ingest
```

Use `python -u` in scheduled jobs so logs appear immediately while the LLM calls
are running.

Output files are written to:

- `out/latest.md`
- `out/latest.html`
- `out/latest.json`

Seen items are tracked in:

- `state/seen_ids.json`

Only real runs update `state/seen_ids.json`. Dry runs are safe for testing and
will not consume the day's items before the email send.

## Common Settings

These values live in `.env`:

```bash
INGEST_BATCH_SIZE=12
INGEST_MAX_ITEMS=60
INGEST_TOP_N=10
INGEST_SCORE_THRESHOLD=5
INGEST_SUBJECT_PREFIX=AI Ingest
```

What they mean:

- `INGEST_BATCH_SIZE`: how many candidates are ranked per LLM call.
- `INGEST_MAX_ITEMS`: maximum fetched candidates before ranking.
- `INGEST_TOP_N`: maximum ranked items included in the digest.
- `INGEST_SCORE_THRESHOLD`: lower bound for items to keep.
- `INGEST_SUBJECT_PREFIX`: email subject prefix.

## Scheduling

Cron example for a Linux server:

```cron
0 9 * * * cd /path/to/ai-ingest && . .venv/bin/activate && python -u -m ai_ingest >> logs/ai-ingest.log 2>&1
```

Create the log directory first:

```bash
mkdir -p logs
```

For systemd timers, GitHub Actions, launchd, or Codex automations, use the same
core command:

```bash
cd /path/to/ai-ingest
. .venv/bin/activate
python -u -m ai_ingest
```

Make sure the scheduler has access to the same `.env` file and network access.

## Troubleshooting

No email arrived:

- Run `python -u -m ai_ingest --dry-run --print` and confirm it fetches and ranks
  items.
- Check whether SMTP is configured. If it is not, the run prints
  `SMTP not configured; skipped email delivery`.
- For Gmail, confirm you are using a Gmail App Password, not your normal login
  password.
- Check Spam, Promotions, All Mail, and Sent. If you send from Gmail to the same
  Gmail account, Gmail may thread the message in a non-obvious place.

The run seems stuck:

- LLM calls can take a while, especially with multiple ranking batches.
- Use `python -u -m ai_ingest` so progress logs flush immediately.
- If one provider is slow, try a faster or cheaper model in `INGEST_MODEL`.

The same items keep appearing:

- Confirm real runs can write `state/seen_ids.json`.
- Dry runs intentionally do not update seen state.

Nothing is ranked:

- Lower `INGEST_SCORE_THRESHOLD`.
- Increase `INGEST_MAX_ITEMS`.
- Check whether sources in `sources.toml` are still reachable.

## Development

Install development dependencies:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest
```

Run a local preview:

```bash
python -u -m ai_ingest --dry-run --print
```

## Security

Do not commit `.env`. It can contain API keys and SMTP credentials. The repo's
`.gitignore` excludes `.env`, generated output, and seen-state files.
