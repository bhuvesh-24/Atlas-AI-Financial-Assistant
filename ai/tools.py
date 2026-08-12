"""Tool schemas + dispatch for the LLM."""
from __future__ import annotations
from typing import Any, Dict, List
import logging

from services import market_data, news, sec, intelligence
from services import gmail_service, calendar_service, drive_service
from services.google_auth import create_auth_url, is_google_configured

logger = logging.getLogger(__name__)


def get_tool_definitions(google_connected: bool = False) -> List[Dict]:
    """Tool definitions for the LLM."""
    tools = [
        {
            "name": "get_stock_quote",
            "description": "Get live stock price, change, market cap, PE and key metrics for a ticker.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker e.g. AAPL, NVDA"},
                },
                "required": ["ticker"],
            },
        },
        {
            "name": "get_company_overview",
            "description": "Deep company profile: business summary, valuation multiples, growth, margins, analyst consensus.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                },
                "required": ["ticker"],
            },
        },
        {
            "name": "compare_stocks",
            "description": "Side-by-side comparison of 2-6 tickers on price, valuation, growth and profitability.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tickers",
                    },
                },
                "required": ["tickers"],
            },
        },
        {
            "name": "get_price_history",
            "description": "Recent OHLCV + simple technicals (SMA20/50, RSI) for a ticker.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "period": {"type": "string", "description": "1d,5d,1mo,3mo,6mo,1y,ytd"},
                },
                "required": ["ticker"],
            },
        },
        {
            "name": "get_company_news",
            "description": "Recent news headlines and summaries for a company.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "days": {"type": "integer", "description": "Lookback days, default 7"},
                },
                "required": ["ticker"],
            },
        },
        {
            "name": "get_market_news",
            "description": "General market / financial headlines.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "general, forex, crypto, merger"},
                },
            },
        },
        {
            "name": "get_sec_filings",
            "description": "List recent SEC filings (10-K, 10-Q, 8-K etc.) with links for a ticker.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "form_type": {"type": "string", "description": "e.g. 10-K, 10-Q, 8-K"},
                },
                "required": ["ticker"],
            },
        },
        {
            "name": "create_price_alert",
            "description": "Create a natural-language price alert for the user (e.g. notify if TSLA moves 5%).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "condition": {"type": "string", "description": "percent_move | price_above | price_below"},
                    "threshold": {"type": "number"},
                    "direction": {"type": "string", "description": "up | down | any"},
                    "note": {"type": "string"},
                },
                "required": ["ticker", "condition", "threshold"],
            },
        },
        {
            "name": "update_watchlist",
            "description": "Add or remove tickers from the user's watchlist.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "add | remove"},
                    "tickers": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["action", "tickers"],
            },
        },
        {
            "name": "initiate_google_connect",
            "description": "Generate a one-time Google sign-in link so the user can connect Gmail/Calendar/Drive/Sheets. Only call when user agrees to connect.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Short reason shown to user"},
                },
            },
        },
        {
            "name": "stress_test_thesis",
            "description": (
                "Stress-test an investment thesis for a stock. Call this when the user states a thesis, "
                "hypothesis, or conviction about a company (e.g. 'my thesis is NVDA grows 40% for 3 years'). "
                "Returns live valuation, growth, news, filings and technical context so you can pressure-test assumptions."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker"},
                    "thesis": {"type": "string", "description": "The user's stated investment thesis or hypothesis"},
                },
                "required": ["ticker", "thesis"],
            },
        },
        {
            "name": "meeting_prep_brief",
            "description": (
                "Generate a pre-meeting / call prep one-pager for a company. "
                "Use when the user mentions an upcoming call, IR discussion, management meeting, "
                "or asks to 'prep me for...' a company conversation."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Company ticker"},
                    "meeting_context": {
                        "type": "string",
                        "description": "What the meeting is about (earnings, partnership, diligence, etc.)",
                    },
                    "counterpart": {
                        "type": "string",
                        "description": "Who they are meeting (IR, CFO, founder, banker, etc.)",
                    },
                },
                "required": ["ticker"],
            },
        },
        {
            "name": "competitor_move_radar",
            "description": (
                "When a major move or news hits one stock, map second-order effects on peers/competitors. "
                "Use when user asks what a move means for rivals, suppliers, or the sector."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Primary ticker that moved"},
                    "event_context": {
                        "type": "string",
                        "description": "What happened, e.g. earnings beat, guidance cut, product launch",
                    },
                    "peer_tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional explicit peers; if empty, infer from sector",
                    },
                },
                "required": ["ticker"],
            },
        },
        {
            "name": "guidance_reality_check",
            "description": (
                "Compare a company's stated guidance / narrative against live valuation, recent news, "
                "and price action. Use when user pastes management commentary or asks if the story still holds."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "stated_narrative": {
                        "type": "string",
                        "description": "Management guidance or thesis to check",
                    },
                },
                "required": ["ticker", "stated_narrative"],
            },
        },
    ]

    if google_connected:
        tools.extend([
            {
                "name": "search_gmail",
                "description": "Search the user's Gmail with a query (e.g. 'from:analyst earnings').",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "list_calendar_events",
                "description": "List upcoming calendar events for the next N days.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer"},
                    },
                },
            },
            {
                "name": "create_calendar_event",
                "description": "Create a calendar event (meeting, reminder).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "start_iso": {"type": "string", "description": "ISO 8601 start"},
                        "end_iso": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["summary", "start_iso", "end_iso"],
                },
            },
            {
                "name": "search_drive",
                "description": "Search Google Drive files by keyword.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "analyze_google_sheet",
                "description": "Preview / analyze a Google Sheet by spreadsheet ID.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {"type": "string"},
                        "range": {"type": "string"},
                    },
                    "required": ["spreadsheet_id"],
                },
            },
        ])
    return tools


async def dispatch_tool(
    name: str,
    arguments: Dict[str, Any],
    user,
    session,
) -> Any:
    """Execute a tool and return JSON-serializable result."""
    try:
        if name == "get_stock_quote":
            return market_data.get_quote(arguments["ticker"])
        if name == "get_company_overview":
            return market_data.get_company_overview(arguments["ticker"])
        if name == "compare_stocks":
            return market_data.compare_tickers(arguments["tickers"])
        if name == "get_price_history":
            return market_data.get_price_history(
                arguments["ticker"], arguments.get("period", "1mo")
            )
        if name == "get_company_news":
            return news.get_company_news(
                arguments["ticker"], arguments.get("days", 7)
            )
        if name == "get_market_news":
            return news.get_market_news(arguments.get("category", "general"))
        if name == "get_sec_filings":
            return sec.get_company_filings(
                arguments["ticker"], arguments.get("form_type", "10-K")
            )
        if name == "create_price_alert":
            from db.models import Alert
            alert = Alert(
                user_id=user.id,
                ticker=arguments["ticker"].upper(),
                condition=arguments["condition"],
                threshold=float(arguments["threshold"]),
                direction=arguments.get("direction", "any"),
                note=arguments.get("note"),
            )
            session.add(alert)
            await session.commit()
            return {
                "status": "created",
                "ticker": alert.ticker,
                "condition": alert.condition,
                "threshold": alert.threshold,
            }
        if name == "update_watchlist":
            wl = list(user.watchlist or [])
            action = arguments["action"]
            for t in arguments["tickers"]:
                t = t.upper()
                if action == "add" and t not in wl:
                    wl.append(t)
                elif action == "remove" and t in wl:
                    wl.remove(t)
            user.watchlist = wl
            await session.commit()
            return {"watchlist": wl}
        if name == "initiate_google_connect":
            if user.google_connected:
                return {"status": "already_connected", "message": "Google account is already connected."}
            if not is_google_configured():
                return {"error": "Google OAuth not configured by the operator."}
            return create_auth_url(str(user.telegram_id))
        if name == "search_gmail":
            return gmail_service.search_emails(
                user, arguments["query"], arguments.get("max_results", 8)
            )
        if name == "list_calendar_events":
            return calendar_service.list_upcoming_events(user, arguments.get("days", 7))
        if name == "create_calendar_event":
            return calendar_service.create_event(
                user,
                arguments["summary"],
                arguments["start_iso"],
                arguments["end_iso"],
                arguments.get("description", ""),
            )
        if name == "search_drive":
            return drive_service.search_files(user, arguments["query"])
        if name == "analyze_google_sheet":
            return drive_service.get_sheet_preview(
                user, arguments["spreadsheet_id"], arguments.get("range", "A1:Z50")
            )
        if name == "stress_test_thesis":
            return intelligence.stress_test_thesis(
                arguments["ticker"], arguments["thesis"]
            )
        if name == "meeting_prep_brief":
            return intelligence.meeting_prep_brief(
                arguments["ticker"],
                arguments.get("meeting_context", ""),
                arguments.get("counterpart", ""),
            )
        if name == "competitor_move_radar":
            return intelligence.competitor_move_radar(
                arguments["ticker"],
                arguments.get("event_context", ""),
                arguments.get("peer_tickers") or [],
            )
        if name == "guidance_reality_check":
            return intelligence.guidance_reality_check(
                arguments["ticker"],
                arguments["stated_narrative"],
            )
        return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return {"error": str(e)}