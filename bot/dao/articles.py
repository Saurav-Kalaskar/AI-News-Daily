"""Async DAO for Article CRUD operations."""
import hashlib
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Article
from bot.dao.session import get_session

log = logging.getLogger(__name__)


class ArticlesDAO:
    """Data access object for articles table."""

    @staticmethod
    def _hash_title(title: str) -> str:
        return hashlib.sha256(title[:80].encode()).hexdigest()[:16]

    async def save_article(
        self,
        title: str,
        url: str | None,
        summary: str | None,
        category: str | None,
        source: str,
        score: int = 0,
    ) -> Optional[Article]:
        """Save a single article. Returns None if duplicate hash exists."""
        h = self._hash_title(title)
        async with get_session() as session:
            # Check for duplicate
            existing = await session.execute(
                select(Article).where(Article.hash == h)
            )
            if existing.scalar_one_or_none():
                log.debug(f"  → Duplicate hash {h}, skipping")
                return None
            article = Article(
                title=title,
                url=url,
                summary=summary,
                category=category,
                source=source,
                score=score,
                hash=h,
            )
            session.add(article)
            await session.commit()
            await session.refresh(article)
            return article

    async def save_many(self, articles: list[dict]) -> list[Article]:
        """Bulk save articles. Skips duplicates silently."""
        saved = []
        for a in articles:
            article = await self.save_article(
                title=a["title"],
                url=a.get("url"),
                summary=a.get("summary"),
                category=a.get("category"),
                source=a["source"],
                score=a.get("score", 0),
            )
            if article:
                saved.append(article)
        log.info(f"  → Saved {len(saved)} articles to DB")
        return saved

    async def search_articles(self, query: str, limit: int = 10) -> list[Article]:
        """Full-text search on title + summary using PostgreSQL to_tsvector."""
        async with get_session() as session:
            # Use to_tsvector for PostgreSQL full-text search
            search_query = select(Article).where(
                func.to_tsvector("english", Article.title).op("@@")(
                    func.plainto_tsquery("english", query)
                )
            ).order_by(Article.created_at.desc()).limit(limit)
            result = await session.execute(search_query)
            return list(result.scalars().all())

    async def get_by_category(self, category: str, limit: int = 10) -> list[Article]:
        """Get articles filtered by category."""
        async with get_session() as session:
            result = await session.execute(
                select(Article)
                .where(Article.category == category)
                .order_by(Article.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_recent(self, limit: int = 5) -> list[Article]:
        """Get most recent articles."""
        async with get_session() as session:
            result = await session.execute(
                select(Article).order_by(Article.created_at.desc()).limit(limit)
            )
            return list(result.scalars().all())

    async def get_article_by_id(self, article_id: int) -> Optional[Article]:
        """Get a single article by ID."""
        async with get_session() as session:
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            return result.scalar_one_or_none()

    async def get_all_categories(self) -> list[str]:
        """Get distinct categories."""
        async with get_session() as session:
            result = await session.execute(
                select(Article.category)
                .where(Article.category.isnot(None))
                .distinct()
            )
            return [r[0] for r in result.fetchall()]