# GMGN Meme Coin Monitor

Zero-cost, read-only meme coin monitoring system using GMGN OpenAPI + GitHub Actions + Email alerts.

## Features

- New Token Detection
- Price Movement Alerts
- Volume Explosion Detection
- Holder Growth Tracking
- Liquidity Change Monitoring
- Smart Money Signals
- Movement Scoring (0-100)
- Email Alerts
- Duplicate Alert Protection

## Setup

### 1. Create GitHub Repository

### 2. Upload Code

### 3. Add GitHub Secrets

| Secret | Description |
|--------|-------------|
| `GMGN_API_KEY` | Your GMGN API Key |
| `SMTP_HOST` | Email SMTP host (e.g., smtp.gmail.com) |
| `SMTP_PORT` | SMTP port (e.g., 587) |
| `SMTP_USERNAME` | Email username |
| `SMTP_PASSWORD` | Email password |
| `ALERT_EMAIL` | Where to send alerts |

### 4. Enable Actions

### 5. Run Workflow Manually

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHAIN` | `sol` | Blockchain to monitor |
| `PRICE_SURGE_5M` | `20` | Price surge threshold % |
| `PRICE_DROP_5M` | `-20` | Price drop threshold % |
| `VOLUME_SPIKE_PERCENT` | `300` | Volume spike threshold % |
| `HOLDER_GROWTH_PERCENT` | `15` | Holder growth threshold % |
| `LIQUIDITY_CHANGE_PERCENT` | `30` | Liquidity change threshold % |
| `MIN_ALERT_SCORE` | `75` | Minimum score for email alerts |
| `ALERT_COOLDOWN_MINUTES` | `30` | Cooldown between alerts |
| `MAX_EMAILS_PER_RUN` | `5` | Max emails per workflow run |
| `DRY_RUN` | `false` | Enable dry-run mode |

### Dry Run

Set `DRY_RUN=true` in GitHub Actions variables to test without sending emails.

## Cost

This project uses:
- Free GitHub Actions (2,000 minutes/month)
- Free GMGN API (read-only endpoints)
- Free SMTP (Gmail, etc.)

**Total cost: $0**

## API

GMGN API endpoints and response fields may change.
Always verify against the current official GMGN API documentation.

**API verified: 2026-08-31**

## License

MIT
