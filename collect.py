"""
AI News Daily - Stage 1: Collection (pure functions, no LLM).
"""
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
import xml.etree.ElementTree as ET

from settings import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HN_KEYWORDS = ["ai", "llm", "agent", "claude", "gpt", "openai", "neural",
               "machine learning", "gemini", "chatgpt", "artificial intelligence"]
SEEN_STORIES_PATH = Path("data/seen_stories.json")
ARXIV_NS = "http://www.w3.org/2005/Atom"

Settings().model_dump()  # validate env


# ── Hacker News ──────────────────────────────────────────────────────────────

def fetch_hn_stories(settings: Settings) -> list[dict[str, Any]]:
    """Fetch top 50 HN stories, filter by AI keywords."""
    log.info("Fetching Hacker News top stories...")
    ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15).json()
    stories = []
    for story_id in ids[:50]:
        item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=15).json()
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


# ── arXiv ─────────────────────────────────────────────────────────────────────

def fetch_arxiv_stories(settings: Settings) -> list[dict[str, Any]]:
    """Fetch recent cs.AI papers from arXiv Atom feed using stdlib ET."""
    log.info("Fetching arXiv cs.AI papers...")
    feed_url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI&max_results=15&sortBy=submittedDate"
    resp = requests.get(feed_url, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    stories = []
    for entry in root.findall(f"{{{ARXIV_NS}}}entry"):
        title_el = entry.find(f"{{{ARXIV_NS}}}title")
        id_el = entry.find(f"{{{ARXIV_NS}}}id")
        link_el = entry.find(f"{{{ARXIV_NS}}}link[@rel='alternate']")
        if link_el is None:
            link_el = entry.find(f"{{{ARXIV_NS}}}link")
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
    log.info(f"  → {len(stories)} arXiv papers")
    return stories


# ── RSS Feeds ─────────────────────────────────────────────────────────────────

RSS_FEEDS = [
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("VentureBeat", "https://venturebeat.com/feed/"),
]


def fetch_rss_stories(settings: Settings) -> list[dict[str, Any]]:
    """Fetch stories from RSS/Atom feeds using stdlib xml.etree."""
    stories = []
    headers = {"User-Agent": "AI-News-Daily/1.0"}
    for source, url in RSS_FEEDS:
        try:
            log.info(f"Fetching RSS: {source}...")
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            # Handle both RSS and Atom formats
            channel = root.find("channel")
            entries = channel.findall("item") if channel is not None else root.findall("entry")
            count = 0
            for entry in entries[:10]:
                title_el = entry.find("title")
                link_el = entry.find("link")
                if title_el is None:
                    title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                # Atom can have link as attribute or element
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


# ── Deduplication ──────────────────────────────────────────────────────────────

def load_seen_stories() -> dict[str, float]:
    """Load seen_stories.json. Returns dict of hash → timestamp."""
    if SEEN_STORIES_PATH.exists():
        return json.loads(SEEN_STORIES_PATH.read_text())
    return {}


def save_seen_stories(seen: dict[str, float]) -> None:
    """Write seen_stories.json atomically."""
    SEEN_STORIES_PATH.write_text(json.dumps(seen, indent=2))


def hash_title(title: str) -> str:
    """SHA256 first 80 chars, return first 16 hex chars."""
    return hashlib.sha256(title[:80].encode()).hexdigest()[:16]


def prune_old_entries(seen: dict[str, float], max_age_days: int = 7) -> None:
    """Remove entries older than max_age_days."""
    cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).timestamp()
    seen.update({k: v for k, v in seen.items() if v >= cutoff})


def deduplicate(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out stories whose title-hash is already in seen_stories.json."""
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


def collect(settings: Settings) -> list[dict[str, Any]]:
    """Stage 1: Aggregate all sources, deduplicate, return new stories."""
    all_stories = fetch_hn_stories(settings) + fetch_arxiv_stories(settings) + fetch_rss_stories(settings)
    return deduplicate(all_stories)