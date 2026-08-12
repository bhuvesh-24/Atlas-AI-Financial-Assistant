"""Financial news from Finnhub (preferred) + yfinance fallback."""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import yfinance as yf

logger = logging.getLogger(__name__)

try:
    import finnhub
    from config import settings
    finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None
except Exception:
    finnhub_client = None


def get_company_news(ticker: str, days: int = 7) -> List[Dict[str, Any]]:
    ticker = ticker.upper().strip()
    articles = []

    # Finnhub first
    if finnhub_client:
        try:
            end = datetime.utcnow().date()
            start = end - timedelta(days=days)
            raw = finnhub_client.company_news(ticker, _from=start.isoformat(), to=end.isoformat())
            for a in (raw or [])[:12]:
                articles.append({
                    "headline": a.get("headline"),
                    "summary": a.get("summary"),
                    "source": a.get("source"),
                    "url": a.get("url"),
                    "datetime": datetime.utcfromtimestamp(a.get("datetime", 0)).isoformat() + "Z" if a.get("datetime") else None,
                    "provider": "finnhub",
                })
            if articles:
                return articles
        except Exception as e:
            logger.warning("Finnhub news failed: %s", e)

    # yfinance fallback
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        for n in news[:10]:
            content = n.get("content") or {}
            articles.append({
                "headline": content.get("title") or n.get("title"),
                "summary": (content.get("summary") or "")[:400],
                "source": (content.get("provider") or {}).get("displayName") if isinstance(content.get("provider"), dict) else n.get("publisher"),
                "url": content.get("canonicalUrl", {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else n.get("link"),
                "datetime": None,
                "provider": "yfinance",
            })
    except Exception as e:
        logger.warning("yfinance news failed: %s", e)

    return articles


def get_market_news(category: str = "general") -> List[Dict[str, Any]]:
    """General market news via Finnhub."""
    if not finnhub_client:
        return [{"headline": "Finnhub API key not configured — set FINNHUB_API_KEY for live market news."}]
    try:
        raw = finnhub_client.general_news(category, min_id=0)
        out = []
        for a in (raw or [])[:15]:
            out.append({
                "headline": a.get("headline"),
                "summary": a.get("summary"),
                "source": a.get("source"),
                "url": a.get("url"),
                "datetime": datetime.utcfromtimestamp(a.get("datetime", 0)).isoformat() + "Z" if a.get("datetime") else None,
            })
        return out
    except Exception as e:
        logger.exception("general_news failed")
        return [{"error": str(e)}]
