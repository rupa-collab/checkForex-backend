# Check Forex Rate Backend


## Features
- Login with JWT
- Store user settings (currencies, thresholds, base currency)
- SendGrid email delivery (Single Sender OK for dev)

## Quick start (local)
1. Create a Postgres DB and set `DATABASE_URL` in `.env`.
2. Copy `.env.example` → `.env` and fill values.
3. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
4. Run:
   ```bash
   uvicorn app.main:app --reload
   ```

## Render
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Uses SendGrid Single Sender by default. Upgrade to a domain later by setting SPF/DKIM/DMARC.
