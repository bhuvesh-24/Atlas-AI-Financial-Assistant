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
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — at minimum TELEGRAM_BOT_TOKEN + ANTHROPIC_API_KEY (or OPENAI)
python main.py
```

Open Telegram → search your bot → start chatting.

## Getting a Telegram bot token

1. Talk to [@BotFather](https://t.me/BotFather)
2. `/newbot` → name + username
3. Copy the token into `.env`

## Google OAuth (optional)

See `integrations/google_setup.md` (create after first run if needed).  
You need a public HTTPS URL for the callback (Railway / Render / ngrok for testing).

## Project layout

```
atlas/
├── main.py              # Entry + polling
├── config.py
├── oauth_server.py      # FastAPI Google callback
├── bot/handlers.py      # Text / voice / docs / images
├── ai/
│   ├── engine.py        # LLM + tool loop
│   ├── tools.py         # Tool schemas & dispatch
│   ├── prompts.py
│   └── memory.py
├── services/
│   ├── market_data.py
│   ├── news.py
│   ├── sec.py
│   ├── documents.py
│   ├── google_auth.py
│   ├── gmail_service.py
│   ├── calendar_service.py
│   └── drive_service.py
├── db/models.py + session.py
├── scheduler/jobs.py    # Alerts + daily brief
├── Dockerfile
└── requirements.txt
```

## Design principles (hackathon)

- **Usefulness & proactivity** over feature count
- Zero-command conversational UX
- Concise, decision-ready answers
- Finance-first; optional verticals later
- Clean modular architecture

## Deployment

See `DEPLOYMENT.md` for Railway / Render / VPS.

## License

Built for the Atlas AI Financial Assistant Hackathon.
