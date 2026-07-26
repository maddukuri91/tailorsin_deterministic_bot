# Telegram Bot Deployment Guide

Since you've removed your Render project, here are your options to redeploy **without using a web dashboard**.

## Option 1: Railway CLI (Recommended - Free Tier Available)

Railway is similar to Render but supports CLI deployment:

```bash
# Install Railway CLI
curl -fsSL https://railway.app/install.sh | sh

# Login (will open browser for OAuth)
railway login

# Initialize project
railway init

# Link to your GitHub repo (or create new)
railway link

# Set environment variables
railway variables set TELEGRAM_BOT_TOKEN=8807201563:AAG7RzrKqAwN-j3-CVHjJ9tjD51d233I-qE
railway variables set TELEGRAM_WEBHOOK_URL=https://your-railway-url.up.railway.app/telegram/webhook
railway variables set CRM_BASE_URL=https://crm.tailorsin.com/tailorsin-api/api

# Deploy
railway up
```

## Option 2: Fly.io CLI (Free Tier Available)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch app (interactive)
fly launch --no-deploy

# Set secrets
fly secrets set TELEGRAM_BOT_TOKEN=8807201563:AAG7RzrKqAwN-j3-CVHjJ9tjD51d233I-qE
fly secrets set CRM_BASE_URL=https://crm.tailorsin.com/tailorsin-api/api

# Deploy
fly deploy
```

## Option 3: Test Locally with ngrok (Quick Testing)

For immediate testing without deploying:

```bash
# Install ngrok
brew install ngrok

# Start your bot locally
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# In another terminal, expose via ngrok
ngrok http 8000

# ngrok will give you a URL like: https://abc123.ngrok.io
# Set that as your webhook:
curl -X POST "https://api.telegram.org/bot8807201563:AAG7RzrKqAwN-j3-CVHjJ9tjD51d233I-qE/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://abc123.ngrok.io/telegram/webhook"}'
```

## Option 4: Run on VPS/Dedicated Server

If you have a VPS:

```bash
# SSH into your server
ssh user@your-server.com

# Clone repo
git clone https://github.com/maddukuri91/tailorsin_deterministic_bot.git
cd tailorsin_deterministic_bot

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # or create manually
nano .env  # Add your environment variables

# Run with systemd (recommended for production)
sudo nano /etc/systemd/system/tailorsin-bot.service
```

Create `/etc/systemd/system/tailorsin-bot.service`:
```ini
[Unit]
Description=Tailorsin Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/tailorsin_deterministic_bot
Environment="TELEGRAM_BOT_TOKEN=8807201563:AAG7RzrKqAwN-j3-CVHjJ9tjD51d233I-qE"
Environment="CRM_BASE_URL=https://crm.tailorsin.com/tailorsin-api/api"
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tailorsin-bot
sudo systemctl start tailorsin-bot

# Check status
sudo systemctl status tailorsin-bot

# View logs
sudo journalctl -u tailorsin-bot -f
```

## After Deployment (Any Option)

Once deployed, set the webhook:

```bash
# Get your deployment URL (example: https://myapp.railway.app)
# Then register webhook:
curl -X POST "https://api.telegram.org/bot8807201563:AAG7RzrKqAwN-j3-CVHjJ9tjD51d233I-qE/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "YOUR_DEPLOYED_URL/telegram/webhook",
    "allowed_updates": ["message", "edited_message", "callback_query"]
  }'
```

## Quick Recommendation

**For fastest setup:** Use Option 3 (ngrok) to test locally first, then deploy to Railway (Option 1).

Once deployed with any option, test your bot in Telegram - it should reply!

## Verify It's Working

```bash
# Check webhook status
curl -s 'https://api.telegram.org/bot8807201563:AAG7RzrKqAwN-j3-CVHjJ9tjD51d233I-qE/getWebhookInfo' | python3 -m json.tool

# Test endpoint
python scripts/diagnose_telegram.py