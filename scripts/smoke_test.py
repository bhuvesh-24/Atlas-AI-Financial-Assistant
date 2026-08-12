"""Quick offline smoke tests (no API keys required for most)."""
import sys
sys.path.insert(0, ".")

from services.market_data import get_quote, compare_tickers
from services.documents import _extract_csv
import tempfile
import os

print("=== Quote test (needs network) ===")
try:
    q = get_quote("AAPL")
    print("AAPL price:", q.get("price"), "change%:", q.get("change_pct"))
except Exception as e:
    print("Quote failed (network?):", e)

print("\n=== Compare ===")
try:
    c = compare_tickers(["AAPL", "MSFT"])
    print("Compared:", [x["ticker"] for x in c.get("comparison", [])])
except Exception as e:
    print(e)

print("\n=== CSV extract ===")
with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
    f.write("date,revenue,cost\n2024-01,100,40\n2024-02,120,45\n2024-03,150,50\n")
    path = f.name
print(_extract_csv(path))
os.unlink(path)
print("\nSmoke tests done.")
