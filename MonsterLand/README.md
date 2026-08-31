# MonsterLand Ad Reward Bot

CLI tool to automatically claim ad rewards on MonsterLand Telegram Mini App.

## Flow

1. Prompt for initData (or use `.auth_token` file / `MONSTERLAND_INITDATA` env var)
2. Create ad task (monetag provider)
3. Get SSE token
4. Fetch ad from AdsGram
5. Report ad events (render, show)
6. Abandon & retry with fallback providers (tads)
7. Wait & check task result
8. Claim reward → get Lumis, Vital, XP

## Usage

```bash
node ad-reward-client.js
```

The script always prompts for fresh initData (tokens expire).

## Files

- `ad-reward-client.js` — Main CLI script
- `api/ads-create.js` — Backend: create ad task endpoint
- `api/ads-result.js` — Backend: check ad task result endpoint

## Auth

The bot uses `Authorization: tma <initData>` header. initData comes from Telegram WebApp's `tgWebAppData`.

## Dependencies

None — uses only Node.js built-in modules (`https`, `readline`, `fs`, `path`, `URL`, `crypto`).