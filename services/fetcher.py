"""
Async fetchers for AI News Daily.
All I/O uses aiohttp for concurrent, non-blocking requests.
"""
import asyncio
import hashlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiohttp

from settings import Settings

log = logging.getLogger(__name__)

HN_KEYWORDS = [
    "ai", "llm", "agent", "claude", "gpt", "openai", "neural",
    "machine learning", "gemini", "chatgpt", "artificial intelligence",
]
SEEN_STORIES_PATH = Path("data/seen_stories.json")
ARXIV_NS = "http://www.w3.org/2005/Atom"


# ── Hacker News ──────────────────────────────────────────────────────────────

async def fetch_hn_stories(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Fetch top 50 HN stories, filter by AI keywords."""
    log.info("Fetching Hacker News top stories...")
    ids = await _fetch_json(session, "https://hacker-news.firebaseio.com/v0/topstories.json", ssl=False)
    stories: list[dict[str, Any]] = []
    for story_id in ids[:50]:
        item = await _fetch_json(session, f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", ssl=False)
        if not item or not item.get("title"):
            continue
        title_lower = item["title"].lower()
        if any(kw in title_lower for kw in HN_KEYWORDS):
            stories.append({
                "title": item["title"],
                "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                "source": "Hacker News",
                "score": item.get("score", 0),
            })
    log.info(f"  → {len(stories)} HN stories after filter")
    return stories


# ── arXiv ───────────────────────────────────────────────────────────────────

async def fetch_arxiv_stories(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Fetch recent cs.AI papers from arXiv Atom feed, apply 24‑hour cutoff, ignore SSL verification."""
    log.info("Fetching arXiv cs.AI papers...")
    feed_url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI&max_results=15&sortBy=submittedDate"
    async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=30), ssl=False) as resp:
        resp.raise_for_status()
        text = await resp.text()
    root = ET.fromstring(text)
    stories: list[dict[str, Any]] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    for entry in root.findall(f"{{{ARXIV_NS}}}entry"):
        title_el = entry.find(f"{{{ARXIV_NS}}}title")
        id_el = entry.find(f"{{{ARXIV_NS}}}id")
        link_el = entry.find(f"{{{ARXIV_NS}}}link[@rel='alternate']")
        if link_el is None:
            link_el = entry.find(f"{{{ARXIV_NS}}}link")
        pub_el = entry.find(f"{{{ARXIV_NS}}}published")
        if pub_el is None or not pub_el.text:
            continue
        try:
            pub_dt = datetime.fromisoformat(pub_el.text.replace('Z', '+00:00'))
        except Exception:
            continue
        if pub_dt < cutoff:
            continue
        title = title_el.text if title_el is not None else ""
        if title:
            title = re.sub(r"\s+", " ", title.strip())
            link = link_el.get("href") if link_el is not None else (id_el.text if id_el is not None else "")
            stories.append({
                "title": title,
                "url": link,
                "source": "arXiv cs.AI",
                "score": 0,
            })
    log.info(f"  → {len(stories)} arXiv papers after time cutoff")
    return stories


# ── RSS Feeds ───────────────────────────────────────────────────────────────

RSS_FEEDS = [
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("VentureBeat", "https://venturebeat.com/feed/"),
]


async def fetch_rss_stories(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Fetch stories from RSS/Atom feeds."""
    stories: list[dict[str, Any]] = []
    for source, url in RSS_FEEDS:
        try:
            log.info(f"Fetching RSS: {source}...")
            text = await _fetch_text(session, url, headers={"User-Agent": "AI-News-Daily/1.0"}, ssl=False)
            root = ET.fromstring(text)
            channel = root.find("channel")
            entries = channel.findall("item") if channel is not None else root.findall("entry")
            count = 0
            for entry in entries[:10]:
                title_el = entry.find("title")
                link_el = entry.find("link")
                if title_el is None:
                    title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                link = None
                if link_el is not None:
                    link = link_el.text or link_el.get("href")
                if link_el is None:
                    link = entry.get("href")
                title = title_el.text if title_el is not None else ""
                if title:
                    title = re.sub(r"\s+", " ", title.strip())
                    stories.append({
                        "title": title,
                        "url": link or "",
                        "source": source,
                        "score": 0,
                    })
                    count += 1
            log.info(f"  → {count} entries from {source}")
        except Exception as e:
            log.warning(f"  → RSS feed failed for {source}: {e}")
    return stories


# ── Deduplication ─────────────────────────────────────────────────────────────

def load_seen_stories() -> dict[str, float]:
    if SEEN_STORIES_PATH.exists():
        return json.loads(SEEN_STORIES_PATH.read_text())
    return {}


def save_seen_stories(seen: dict[str, float]) -> None:
    SEEN_STORIES_PATH.write_text(json.dumps(seen, indent=2))


def hash_title(title: str) -> str:
    return hashlib.sha256(title[:80].encode()).hexdigest()[:16]


def prune_old_entries(seen: dict[str, float], max_age_days: int = 7) -> None:
    cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).timestamp()
    seen.update({k: v for k, v in seen.items() if v >= cutoff})


def deduplicate(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = load_seen_stories()
    prune_old_entries(seen)
    new_stories = []
    now = datetime.utcnow().timestamp()
    for story in stories:
        h = hash_title(story["title"])
        if h not in seen:
            seen[h] = now
            new_stories.append(story)
    save_seen_stories(seen)
    log.info(f"  → {len(new_stories)} new stories after dedup ({len(stories)} total)")
    return new_stories


# ── Collect orchestrator ─────────────────────────────────────────────────────

async def collect(settings: Settings) -> list[dict[str, Any]]:
    """Aggregate all sources, deduplicate, return new stories."""
    async with aiohttp.ClientSession() as session:
        all_stories = await asyncio.gather(
            fetch_hn_stories(session),
            fetch_arxiv_stories(session),
            fetch_rss_stories(session),
        )
    flat = [s for sublist in all_stories for s in sublist]
    return deduplicate(flat)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _fetch_json(session: aiohttp.ClientSession, url: str, ssl: bool = True) -> Any:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30), ssl=ssl) as resp:
        resp.raise_for_status()
        return await resp.json()


async def _fetch_text(session: aiohttp.ClientSession, url: str, headers: dict | None = None, ssl: bool = True) -> str:
    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30), ssl=ssl) as resp:
        resp.raise_for_status()
        return await resp.text()
