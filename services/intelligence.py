"""Standout intelligence features for Atlas."""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from services import market_data, news, sec

logger = logging.getLogger(__name__)


def stress_test_thesis(ticker: str, thesis: str) -> Dict[str, Any]:
    ticker = ticker.upper().strip()
    overview = market_data.get_company_overview(ticker)
    quote = market_data.get_quote(ticker)
    recent_news = news.get_company_news(ticker, days=14)
    filings = sec.get_company_filings(ticker, form_type="8-K", limit=3)
    history = market_data.get_price_history(ticker, period="6mo")

    return {
        "ticker": ticker,
        "thesis_stated_by_user": thesis,
        "as_of": datetime.utcnow().isoformat() + "Z",
        "current_price": quote.get("price"),
        "change_pct_today": quote.get("change_pct"),
        "market_cap": overview.get("market_cap"),
        "valuation": {
            "trailing_pe": overview.get("pe_ratio"),
            "forward_pe": overview.get("forward_pe"),
            "ev_to_ebitda": overview.get("ev_to_ebitda"),
            "price_to_sales": overview.get("price_to_sales"),
            "peg": overview.get("peg_ratio"),
        },
        "growth_and_quality": {
            "revenue_growth": overview.get("revenue_growth"),
            "earnings_growth": overview.get("earnings_growth"),
            "operating_margins": overview.get("operating_margins"),
            "profit_margins": overview.get("profit_margins"),
            "roe": overview.get("roe"),
            "debt_to_equity": overview.get("debt_to_equity"),
        },
        "street": {
            "recommendation": overview.get("recommendation"),
            "target_mean_price": overview.get("target_mean_price"),
            "analyst_count": overview.get("analyst_count"),
        },
        "business_snapshot": (overview.get("summary") or "")[:900],
        "sector": overview.get("sector"),
        "industry": overview.get("industry"),
        "recent_news_headlines": [
            {"headline": n.get("headline"), "summary": (n.get("summary") or "")[:200]}
            for n in (recent_news or [])[:6]
        ],
        "recent_8k_filings": filings.get("filings", [])[:3] if isinstance(filings, dict) else [],
        "technical_context": {
            "last_close": history.get("last_close"),
            "sma20": history.get("sma20"),
            "sma50": history.get("sma50"),
            "rsi_14": history.get("rsi_14"),
        },
        "instruction_for_llm": (
            "Using ONLY the evidence above, stress-test the user's thesis. "
            "Return: (1) 3–5 key assumptions, (2) strongest vs weakest, "
            "(3) biggest 6–12 month invalidation risk, "
            "(4) verdict: Supported / Partially Supported / Stretched / Contradicted, "
            "(5) one concrete monitoring point. Do not invent numbers."
        ),
    }


def meeting_prep_brief(
    ticker: str,
    meeting_context: str = "",
    counterpart: str = "",
) -> Dict[str, Any]:
    ticker = ticker.upper().strip()
    overview = market_data.get_company_overview(ticker)
    quote = market_data.get_quote(ticker)
    recent_news = news.get_company_news(ticker, days=21)
    filings_8k = sec.get_company_filings(ticker, form_type="8-K", limit=4)
    filings_10q = sec.get_company_filings(ticker, form_type="10-Q", limit=1)

    return {
        "ticker": ticker,
        "company_name": overview.get("name"),
        "meeting_context": meeting_context or "General company discussion",
        "counterpart": counterpart or "Not specified",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "snapshot": {
            "price": quote.get("price"),
            "change_pct": quote.get("change_pct"),
            "market_cap": overview.get("market_cap"),
            "pe": overview.get("pe_ratio"),
            "forward_pe": overview.get("forward_pe"),
            "revenue_growth": overview.get("revenue_growth"),
            "operating_margins": overview.get("operating_margins"),
            "recommendation": overview.get("recommendation"),
            "target_mean": overview.get("target_mean_price"),
        },
        "business_one_liner": (overview.get("summary") or "")[:500],
        "sector_industry": f"{overview.get('sector')} / {overview.get('industry')}",
        "recent_news": [
            {
                "headline": n.get("headline"),
                "summary": (n.get("summary") or "")[:220],
                "source": n.get("source"),
            }
            for n in (recent_news or [])[:7]
        ],
        "recent_filings": {
            "8K": filings_8k.get("filings", [])[:3] if isinstance(filings_8k, dict) else [],
            "10Q": filings_10q.get("filings", [])[:1] if isinstance(filings_10q, dict) else [],
        },
        "instruction_for_llm": (
            "Produce a tight PRE-MEETING ONE-PAGER:\n"
            "1. Situation Snapshot (3–4 bullets)\n"
            "2. Hot Buttons (3)\n"
            "3. Sharp Questions to Ask (4)\n"
            "4. Watch-outs / Landmines (2–3)\n"
            "5. Suggested Opening Line\n"
            "Under 350 words. Specific. No invented facts."
        ),
    }


def competitor_move_radar(
    ticker: str,
    event_context: str = "",
    peer_tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    ticker = ticker.upper().strip()
    overview = market_data.get_company_overview(ticker)
    quote = market_data.get_quote(ticker)
    news_items = news.get_company_news(ticker, days=7)

    peers = [p.upper() for p in (peer_tickers or [])][:6]
    if not peers:
        sector = (overview.get("sector") or "").lower()
        if "technolog" in sector or "semiconductor" in sector:
            peers = [p for p in ["NVDA", "AMD", "AVGO", "TSM", "INTC", "QCOM"] if p != ticker][:4]
        elif "consumer" in sector:
            peers = [p for p in ["AAPL", "AMZN", "MSFT", "GOOGL"] if p != ticker][:4]

    peer_snapshots = []
    for p in peers:
        q = market_data.get_quote(p)
        peer_snapshots.append({
            "ticker": p,
            "price": q.get("price"),
            "change_pct": q.get("change_pct"),
            "name": q.get("name"),
        })

    return {
        "primary": {
            "ticker": ticker,
            "name": overview.get("name"),
            "price": quote.get("price"),
            "change_pct": quote.get("change_pct"),
            "sector": overview.get("sector"),
            "industry": overview.get("industry"),
        },
        "event_context": event_context or "Not specified",
        "recent_headlines": [
            {"headline": n.get("headline"), "summary": (n.get("summary") or "")[:180]}
            for n in (news_items or [])[:5]
        ],
        "peers": peer_snapshots,
        "instruction_for_llm": (
            "Explain second-order effects: who benefits, who is hurt, "
            "what to watch next 1–4 weeks. Specific. Two actionable monitoring points."
        ),
    }


def guidance_reality_check(ticker: str, stated_narrative: str) -> Dict[str, Any]:
    ticker = ticker.upper().strip()
    overview = market_data.get_company_overview(ticker)
    quote = market_data.get_quote(ticker)
    hist = market_data.get_price_history(ticker, period="3mo")
    news_items = news.get_company_news(ticker, days=14)

    return {
        "ticker": ticker,
        "stated_narrative": stated_narrative,
        "live": {
            "price": quote.get("price"),
            "change_pct": quote.get("change_pct"),
            "pe": overview.get("pe_ratio"),
            "forward_pe": overview.get("forward_pe"),
            "revenue_growth": overview.get("revenue_growth"),
            "operating_margins": overview.get("operating_margins"),
            "recommendation": overview.get("recommendation"),
            "target_mean": overview.get("target_mean_price"),
        },
        "technical": {
            "sma20": hist.get("sma20"),
            "sma50": hist.get("sma50"),
            "rsi_14": hist.get("rsi_14"),
        },
        "recent_news": [{"headline": n.get("headline")} for n in (news_items or [])[:6]],
        "instruction_for_llm": (
            "Reality-check the stated narrative vs live data. "
            "Return: (1) Alignments, (2) Tensions, (3) What would falsify it, "
            "(4) Verdict: Credible / Stretched / Breaking. Be blunt."
        ),
    }