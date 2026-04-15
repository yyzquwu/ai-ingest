from __future__ import annotations

import argparse
import asyncio
import smtplib
from datetime import datetime
from email.message import EmailMessage

from ai_ingest.config import load_settings
from ai_ingest.llm import rank_items, synthesize
from ai_ingest.render import render_markdown, write_outputs
from ai_ingest.sources import fetch_candidates, load_seen_ids, load_source_specs, save_seen_ids


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a streamlined ML/AI ingest run.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch, rank, and write files without sending email.")
    parser.add_argument("--print", dest="print_output", action="store_true", help="Print the markdown digest to stdout.")
    return parser


def send_email(
    host: str,
    port: int,
    use_starttls: bool,
    username: str | None,
    password: str | None,
    sender: str,
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    if use_starttls:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if username:
                smtp.login(username, password or "")
            smtp.send_message(message)
    else:
        with smtplib.SMTP_SSL(host, port) as smtp:
            if username:
                smtp.login(username, password or "")
            smtp.send_message(message)


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings()

    specs = load_source_specs(settings.sources_file)
    seen_ids = load_seen_ids(settings.seen_file)
    candidates = asyncio.run(fetch_candidates(specs, seen_ids, settings.max_items))

    print(f"[info] fetched {len(candidates)} unseen candidates")
    if not candidates:
        return

    ranked = rank_items(
        items=candidates,
        model=settings.model,
        batch_size=settings.batch_size,
        score_threshold=settings.score_threshold,
    )
    print(f"[info] kept {len(ranked)} ranked items")
    if not ranked:
        save_seen_ids(settings.seen_file, seen_ids | {item.id for item in candidates})
        return

    top_ranked = ranked[: settings.top_n]
    summary = synthesize(top_ranked, model=settings.model, top_n=settings.top_n)
    date_label = datetime.now().strftime("%B %d, %Y")
    markdown_path, html_path, json_path = write_outputs(settings.output_dir, date_label, summary, top_ranked)

    subject = f"{settings.subject_prefix} - {date_label}"
    markdown = render_markdown(date_label, summary, top_ranked)
    html = html_path.read_text()

    if args.print_output:
        print()
        print(markdown)

    if not args.dry_run and settings.smtp_enabled:
        send_email(
            host=settings.smtp_host or "",
            port=settings.smtp_port,
            use_starttls=settings.smtp_use_starttls,
            username=settings.smtp_username,
            password=settings.smtp_password,
            sender=settings.smtp_from or "",
            recipient=settings.ingest_to or "",
            subject=subject,
            text_body=markdown,
            html_body=html,
        )
        print(f"[info] sent email to {settings.ingest_to}")
    elif not settings.smtp_enabled:
        print("[info] SMTP not configured; skipped email delivery")

    save_seen_ids(settings.seen_file, seen_ids | {item.id for item in candidates})
    print(f"[info] wrote {markdown_path.name}, {html_path.name}, {json_path.name}")


if __name__ == "__main__":
    main()
