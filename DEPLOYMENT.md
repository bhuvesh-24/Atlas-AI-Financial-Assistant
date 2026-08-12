# Deploying Atlas

## Option 1 — Railway (recommended for demo)

1. Install CLI: `npm i -g @railway/cli`
2. `railway login`
3. From project root: `railway init` → `railway up`
4. In Railway dashboard:
   - Add environment variables from `.env.example`
   - Attach a **persistent volume** mounted at `/app/data` (otherwise SQLite is wiped on redeploy)
   - Generate a public domain for the service (needed for Google OAuth callback)
5. Set `GOOGLE_REDIRECT_URI=https://your-railway-domain.up.railway.app/oauth/callback`
6. In Google Cloud Console → Credentials → Authorized redirect URIs, add the same URL.

Bot runs via polling — no webhook required.

## Option 2 — Render.com

- New **Web Service** from GitHub repo (or Docker)
- Build: `pip install -r requirements.txt`
- Start: `python main.py`
- Add disk for `/app/data`
- Same env vars + public URL for OAuth

## Option 3 — VPS (long-lived)

```bash
# Ubuntu example
sudo apt update && sudo apt install python3.11-venv
git clone <your-repo> && cd atlas
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill secrets
# systemd unit
sudo tee /etc/systemd/system/atlas.service <<EOF
[Unit]
Description=Atlas Telegram Bot
After=network.target
[Service]
WorkingDirectory=/home/ubuntu/atlas
ExecStart=/home/ubuntu/atlas/.venv/bin/python main.py
Restart=always
User=ubuntu
EnvironmentFile=/home/ubuntu/atlas/.env
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now atlas
```

For Google OAuth on a VPS, put nginx + Let’s Encrypt in front of port 8000 and set `GOOGLE_REDIRECT_URI` accordingly.

## Post-deploy checklist

- [ ] Bot responds to a plain text message
- [ ] Fresh onboarding flow works
- [ ] Stock quote returns live data
- [ ] PDF upload summarizes
- [ ] (Optional) Google connect link works end-to-end
- [ ] Delete local test DB before demo so judges see clean onboarding
- [ ] Share `t.me/YourBotUsername` + short demo video
