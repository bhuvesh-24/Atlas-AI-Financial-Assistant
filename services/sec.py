"""SEC EDGAR research helpers (best-effort, free)."""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "AtlasFinancialAssistant/1.0 (hackathon; contact@example.com)",
    "Accept-Encoding": "gzip, deflate",
}


def get_company_filings(ticker: str, form_type: str = "10-K", limit: int = 5) -> Dict[str, Any]:
    """
    Look up recent filings via the SEC company tickers + submissions API.
    Returns metadata + links; full text extraction is left to document upload flow.
    """
    ticker = ticker.upper().strip()
    try:
        # Resolve CIK
        with httpx.Client(timeout=20, headers=HEADERS) as client:
            tickers_resp = client.get("https://www.sec.gov/files/company_tickers.json")
            tickers_resp.raise_for_status()
            data = tickers_resp.json()
            cik = None
            name = None
            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker:
                    cik = str(entry["cik_str"]).zfill(10)
                    name = entry.get("title")
                    break
            if not cik:
                return {"ticker": ticker, "error": "CIK not found"}

            # Submissions
            sub_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            sub = client.get(sub_url)
            sub.raise_for_status()
            sub_data = sub.json()
            recent = sub_data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            primary = recent.get("primaryDocument", [])

            filings = []
            for i, form in enumerate(forms):
                if form_type and form_type.upper() not in form.upper():
                    continue
                if len(filings) >= limit:
                    break
                acc = accessions[i].replace("-", "")
                doc = primary[i] if i < len(primary) else ""
                url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}"
                filings.append({
                    "form": form,
                    "filing_date": dates[i] if i < len(dates) else None,
                    "accession": accessions[i],
                    "document_url": url,
                    "primary_document": doc,
                })

            return {
                "ticker": ticker,
                "cik": cik,
                "company_name": name or sub_data.get("name"),
                "filings": filings,
                "source": "SEC EDGAR",
            }
    except Exception as e:
        logger.exception("SEC lookup failed for %s", ticker)
        return {"ticker": ticker, "error": str(e)}


def get_latest_10k_summary_hint(ticker: str) -> str:
    """Helper text for the AI when user asks about 10-K risks etc."""
    data = get_company_filings(ticker, "10-K", limit=1)
    if data.get("filings"):
        f = data["filings"][0]
        return (
            f"Latest 10-K for {ticker} filed on {f.get('filing_date')}. "
            f"Primary document: {f.get('document_url')}. "
            "Advise the user to upload the PDF for detailed Item 1A risk extraction, "
            "or I can open the URL if needed."
        )
    return f"Could not locate recent 10-K for {ticker}."
