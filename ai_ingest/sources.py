from __future__ import annotations

import asyncio
import json
import tomllib
from collections import deque
from datetime import datetime
from pathlib import Path

import feedparser
import httpx
from bs4 import BeautifulSoup

from ai_ingest.models import RawItem, SourceSpec


HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_COMMENTS_URL = "https://hn.algolia.com/api/v1/search"
USER_AGENT = "ai-ingest/0.1"


def load_source_specs(path: Path) -> list[SourceSpec]:
    data = tomllib.loads(path.read_text())
    specs = []
    for item in data.get("source", []):
        specs.append(
            SourceSpec(
                id=item["id"],
                label=item["label"],
                kind=item["kind"],
                url=item.get("url"),
                limit=int(item.get("limit", 5)),
                query=item.get("query"),
            )
        )
    return specs


def load_seen_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text())
    return set(payload.get("ids", []))


def save_seen_ids(path: Path, ids: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ids": sorted(ids),
        "updated_at": datetime.now().isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2))


def strip_html(value: str) -> str:
    if not value:
        return ""
    if "<" not in value:
        return " ".join(value.split())[:1500]
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return " ".join(text.split())[:1500]


async def fetch_candidates(specs: list[SourceSpec], seen_ids: set[str], max_items: int) -> list[RawItem]:
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers, timeout=20, follow_redirects=True) as client:
        tasks = [_fetch_source(client, spec, seen_ids) for spec in specs]
        groups = await asyncio.gather(*tasks)

    return _balance_candidates(groups, max_items)


def _balance_candidates(groups: list[list[RawItem]], max_items: int) -> list[RawItem]:
    queues = [deque(group) for group in groups if group]
    deduped: list[RawItem] = []
    seen: set[str] = set()

    while queues and len(deduped) < max_items:
        next_round: list[deque[RawItem]] = []
        for queue in queues:
            while queue:
                item = queue.popleft()
                key = item.id or item.url
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(item)
                break
            if queue:
                next_round.append(queue)
            if len(deduped) >= max_items:
                break
        queues = next_round

    return deduped


async def _fetch_source(client: httpx.AsyncClient, spec: SourceSpec, seen_ids: set[str]) -> list[RawItem]:
    try:
        if spec.kind == "rss":
            return await _fetch_rss(client, spec, seen_ids)
        if spec.kind == "hn_jobs":
            return await _fetch_hn_jobs(client, spec, seen_ids)
    except Exception as exc:
        print(f"[warn] {spec.id}: {exc}")
    return []


async def _fetch_rss(client: httpx.AsyncClient, spec: SourceSpec, seen_ids: set[str]) -> list[RawItem]:
    if not spec.url:
        return []
    response = await client.get(spec.url)
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    items: list[RawItem] = []
    for entry in feed.entries:
        article_id = entry.get("id") or entry.get("link") or ""
        if not article_id or article_id in seen_ids:
            continue
        summary = ""
        if getattr(entry, "content", None):
            summary = entry.content[0].get("value", "")
        elif getattr(entry, "summary", None):
            summary = entry.summary or ""
        items.append(
            RawItem(
                id=article_id,
                source=spec.id,
                source_label=spec.label,
                title=entry.get("title", "Untitled"),
                url=entry.get("link", article_id),
                published=entry.get("published", ""),
                summary=strip_html(summary),
            )
        )
        if len(items) >= spec.limit:
            break
    return items


async def _fetch_hn_jobs(client: httpx.AsyncClient, spec: SourceSpec, seen_ids: set[str]) -> list[RawItem]:
    thread_id = await _current_hn_hiring_thread_id(client)
    if not thread_id:
        return []

    response = await client.get(
        HN_COMMENTS_URL,
        params={
            "tags": f"comment,story_{thread_id}",
            "query": spec.query or "AI OR machine learning OR LLM",
            "hitsPerPage": spec.limit * 2,
        },
    )
    response.raise_for_status()
    hits = response.json().get("hits", [])
    items: list[RawItem] = []
    for hit in hits:
        article_id = f"hn_{hit.get('objectID', '')}"
        if not article_id or article_id in seen_ids:
            continue
        summary = strip_html(hit.get("comment_text", ""))
        if not summary:
            continue
        items.append(
            RawItem(
                id=article_id,
                source=spec.id,
                source_label=spec.label,
                title=f"HN Job - {hit.get('author', 'anonymous')}",
                url=f"https://news.ycombinator.com/item?id={hit['objectID']}",
                published=hit.get("created_at", ""),
                summary=summary,
            )
        )
        if len(items) >= spec.limit:
            break
    return items


async def _current_hn_hiring_thread_id(client: httpx.AsyncClient) -> str:
    response = await client.get(
        HN_SEARCH_URL,
        params={
            "query": "who is hiring",
            "tags": "ask_hn",
            "hitsPerPage": 1,
        },
    )
    response.raise_for_status()
    hits = response.json().get("hits", [])
    if not hits:
        return ""
    return hits[0].get("objectID", "")
