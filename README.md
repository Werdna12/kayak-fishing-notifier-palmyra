# Kayak Fishing Weekend Notifier (Palmyra, WA)

Free automated system that checks every day at **4pm AWST** and emails you **only once** when an upcoming weekend (within 14 days) meets safe + good kayak fishing conditions in the Palmyra / Swan River / Cockburn Sound area.

## Features
- Uses free Open-Meteo weather + marine API (no keys needed)
- Safe kayak guidelines with flexible temperature (you handle cold well)
- Daily check at 4pm AWST via GitHub Actions (free)
- Notifies **only once** per ideal weekend (deduplication)
- Includes moon phase for fish activity context
- Email via free Gmail SMTP

## Quick Setup (5 minutes)

### 1. Add GitHub Secrets
Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add two secrets:
- `GMAIL_USER` → your full Gmail address
- `GMAIL_APP_PASSWORD` → 16-character Gmail App Password (create one at Google Account → Security → App passwords)

### 2. Enable the Workflow
- Go to the **Actions** tab
- Click **"I understand my workflows, go ahead and enable them"** if prompted
- The workflow will now run automatically every day at 4pm AWST

### 3. Test it
Click **"Run workflow"** → **Run workflow** (manual trigger) to test immediately.

## Customization
Edit the top of `kayak_fishing_notifier.py` to change thresholds if desired.

## Files included
- `kayak_fishing_notifier.py` – main script
- `.github/workflows/daily_kayak_check.yml` – scheduler
- `README.md` – this file

Tight lines and stay safe! 🎣
