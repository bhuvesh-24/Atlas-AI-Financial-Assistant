# Atlas — AI Financial Assistant for Telegram

A conversational AI financial analyst that lives inside Telegram.  
No slash commands, no buttons, no menus — just natural language.

## What it does

| Capability | Description |
|---|---|
| **Natural onboarding** | Learns role, watchlist, preferences through conversation |
| **Live market data** | Quotes, fundamentals, comparisons, technicals (yfinance) |
| **News + context** | Company & market news with “why it matters” |
| **SEC EDGAR** | Recent 10-K / 10-Q / 8-K filings with links |
| **Document intelligence** | PDF, DOCX, XLSX, CSV upload → summary + Q&A |
| **Image analysis** | Charts / screenshots (vision-ready path) |
| **Voice** | Whisper transcription via Groq |
| **Price alerts** | “Alert me if TSLA moves 5%” → background monitoring |
| **Daily briefing** | Personalized morning brief on schedule |
| **Google workspace** | Gmail search, Calendar, Drive, Sheets (OAuth) |
| **Persistent memory** | Profile, watchlist, conversation history in SQLite |
| **Thesis Stress-Tester** | State a thesis → Atlas pressure-tests assumptions with live data |
| **Meeting Prep One-Pager** | “Prep me for my call with Apple IR” → situation, questions, landmines |

## Quick start (local)

```bash
cd atlas
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — TELEGRAM_BOT_TOKEN + GROQ_API_KEY
python main.py
```

Open Telegram → search your bot → start chatting.

### LLM setup (free)

1. Get a free key at [console.groq.com](https://console.groq.com)
2. In `.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant
GROQ_FALLBACK_MODELS=openai/gpt-oss-20b,llama-3.3-70b-versatile
```

These are **current Groq production models** (fast + free-tier friendly).  
If you hit rate limits (429), wait a few minutes and try again — free tiers reset periodically.

## Getting a Telegram bot token

1. Talk to [@BotFather](https://t.me/BotFather)
2. `/newbot` → name + username
3. Copy the token into `.env`

## Google OAuth (optional)

See `integrations/google_setup.md`.  
You need a public HTTPS URL for the callback (Railway / Render / ngrok for testing).

## Project layout

```
atlas/
├── main.py              # Entry + polling
├── config.py
├── oauth_server.py      # FastAPI Google callback
├── bot/handlers.py      # Text / voice / docs / images
├── ai/
│   ├── engine.py        # LLM + tool loop + model fallbacks
│   ├── tools.py
│   ├── prompts.py
│   └── memory.py
├── services/
├── db/
├── scheduler/
├── Dockerfile
└── requirements.txt
```

## Deployment

See `DEPLOYMENT.md` for Railway / Render / VPS.

## License

Built for the Atlas AI Financial Assistant Hackathon.
