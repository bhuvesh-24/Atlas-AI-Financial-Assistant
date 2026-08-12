"""Live market data via yfinance + optional Finnhub."""
from __future__ import annotations
import yfinance as yf
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

try:
    import finnhub
    from config import settings
    finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY) if settings.FINNHUB_API_KEY else None
except Exception:
    finnhub_client = None


def get_quote(ticker: str) -> Dict[str, Any]:
    """Get current quote and basic info for a ticker."""
    ticker = ticker.upper().strip()
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="5d")
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change = None
        change_pct = None
        if price and prev_close:
            change = round(price - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2)

        return {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "price": price,
            "previous_close": prev_close,
            "change": change,
            "change_pct": change_pct,
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume") or info.get("regularMarketVolume"),
            "avg_volume": info.get("averageVolume"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "exchange": info.get("exchange"),
            "as_of": datetime.utcnow().isoformat() + "Z",
            "source": "yfinance",
        }
    except Exception as e:
        logger.exception("get_quote failed for %s", ticker)
        return {"ticker": ticker, "error": str(e)}


def get_company_overview(ticker: str) -> Dict[str, Any]:
    """Richer company profile + key financials."""
    ticker = ticker.upper().strip()
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        financials = {}
        try:
            fin = t.financials
            if fin is not None and not fin.empty:
                # Take latest year
                latest = fin.iloc[:, 0]
                financials = {
                    "revenue": float(latest.get("Total Revenue", 0) or 0),
                    "gross_profit": float(latest.get("Gross Profit", 0) or 0),
                    "operating_income": float(latest.get("Operating Income", 0) or 0),
                    "net_income": float(latest.get("Net Income", 0) or 0),
                    "period": str(fin.columns[0].date()) if hasattr(fin.columns[0], "date") else str(fin.columns[0]),
                }
        except Exception:
            pass

        return {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName"),
            "summary": (info.get("longBusinessSummary") or "")[:1200],
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "website": info.get("website"),
            "employees": info.get("fullTimeEmployees"),
            "country": info.get("country"),
            "city": info.get("city"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "ev_to_ebitda": info.get("enterpriseToEbitda"),
            "profit_margins": info.get("profitMargins"),
            "operating_margins": info.get("operatingMargins"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "target_mean_price": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey"),
            "analyst_count": info.get("numberOfAnalystOpinions"),
            "financials_latest": financials,
            "source": "yfinance",
        }
    except Exception as e:
        logger.exception("get_company_overview failed for %s", ticker)
        return {"ticker": ticker, "error": str(e)}


def compare_tickers(tickers: List[str]) -> Dict[str, Any]:
    """Side-by-side comparison of multiple tickers."""
    results = []
    for tk in tickers[:6]:  # limit
        q = get_quote(tk)
        ov = get_company_overview(tk)
        results.append({
            "ticker": tk.upper(),
            "name": q.get("name"),
            "price": q.get("price"),
            "change_pct": q.get("change_pct"),
            "market_cap": ov.get("market_cap"),
            "pe_ratio": ov.get("pe_ratio"),
            "forward_pe": ov.get("forward_pe"),
            "ev_to_ebitda": ov.get("ev_to_ebitda"),
            "profit_margins": ov.get("profit_margins"),
            "operating_margins": ov.get("operating_margins"),
            "revenue_growth": ov.get("revenue_growth"),
            "roe": ov.get("roe"),
            "recommendation": ov.get("recommendation"),
            "sector": ov.get("sector"),
        })
    return {"comparison": results, "as_of": datetime.utcnow().isoformat() + "Z"}


def get_price_history(ticker: str, period: str = "1mo") -> Dict[str, Any]:
    """OHLCV history for technical context."""
    ticker = ticker.upper().strip()
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        if hist.empty:
            return {"ticker": ticker, "error": "No history"}
        records = []
        for idx, row in hist.tail(30).iterrows():
            records.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        # Simple technicals
        closes = hist["Close"]
        sma20 = float(closes.tail(20).mean()) if len(closes) >= 20 else None
        sma50 = float(closes.tail(50).mean()) if len(closes) >= 50 else None
        last = float(closes.iloc[-1])
        rsi = _compute_rsi(closes)
        return {
            "ticker": ticker,
            "period": period,
            "last_close": last,
            "sma20": round(sma20, 2) if sma20 else None,
            "sma50": round(sma50, 2) if sma50 else None,
            "rsi_14": round(rsi, 1) if rsi else None,
            "history": records,
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def _compute_rsi(series, period: int = 14) -> Optional[float]:
    try:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    except Exception:
        return None


def get_earnings_calendar(ticker: Optional[str] = None) -> Dict[str, Any]:
    """Upcoming earnings (best-effort via yfinance)."""
    if ticker:
        try:
            t = yf.Ticker(ticker.upper())
            cal = t.calendar
            if cal is not None and not (hasattr(cal, "empty") and cal.empty):
                return {"ticker": ticker.upper(), "calendar": str(cal)}
        except Exception:
            pass
    return {"message": "Earnings calendar limited without Finnhub premium. Use company-specific requests."}
