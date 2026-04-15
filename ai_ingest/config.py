from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent


@dataclass(slots=True)
class Settings:
    model: str
    batch_size: int
    max_items: int
    top_n: int
    score_threshold: int
    subject_prefix: str
    sources_file: Path
    output_dir: Path
    seen_file: Path
    smtp_host: str | None
    smtp_port: int
    smtp_use_starttls: bool
    smtp_username: str | None
    smtp_password: str | None
    smtp_from: str | None
    ingest_to: str | None

    @property
    def smtp_enabled(self) -> bool:
        return bool(
            self.smtp_host
            and self.smtp_from
            and self.ingest_to
            and (self.smtp_password or not self.smtp_username)
        )


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env(primary: str, legacy: str | None = None, default: str | None = None) -> str | None:
    value = os.getenv(primary)
    if value not in (None, ""):
        return value
    if legacy:
        legacy_value = os.getenv(legacy)
        if legacy_value not in (None, ""):
            return legacy_value
    return default


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    model = (_env("INGEST_MODEL", "DIGEST_MODEL", "") or "").strip()
    if not model:
        raise ValueError("Set INGEST_MODEL in .env before running ai-ingest.")

    return Settings(
        model=model,
        batch_size=max(1, int(_env("INGEST_BATCH_SIZE", "DIGEST_BATCH_SIZE", "12") or "12")),
        max_items=max(1, int(_env("INGEST_MAX_ITEMS", "DIGEST_MAX_ITEMS", "60") or "60")),
        top_n=max(1, int(_env("INGEST_TOP_N", "DIGEST_TOP_N", "10") or "10")),
        score_threshold=max(1, int(_env("INGEST_SCORE_THRESHOLD", "DIGEST_SCORE_THRESHOLD", "5") or "5")),
        subject_prefix=(_env("INGEST_SUBJECT_PREFIX", "DIGEST_SUBJECT_PREFIX", "AI Ingest") or "AI Ingest").strip() or "AI Ingest",
        sources_file=ROOT / "sources.toml",
        output_dir=ROOT / "out",
        seen_file=ROOT / "state" / "seen_ids.json",
        smtp_host=os.getenv("SMTP_HOST") or None,
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_use_starttls=_as_bool(os.getenv("SMTP_USE_STARTTLS"), False),
        smtp_username=os.getenv("SMTP_USERNAME") or None,
        smtp_password=os.getenv("SMTP_PASSWORD") or None,
        smtp_from=os.getenv("SMTP_FROM") or None,
        ingest_to=_env("INGEST_TO", "DIGEST_TO"),
    )
