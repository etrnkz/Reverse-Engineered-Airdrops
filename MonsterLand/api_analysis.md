# API Analysis — MonsterLand Telegram Mini App

## Base URL
```
https://lets.playmonsterland.com
```

## Authentication
Telegram `initData` is sent as `Authorization: tma <initData>` HTTP header on API calls:
- `query_id`
- `user` (JSON object)
- `auth_date`
- `hash`
- `signature`

The `.auth_token` file stores the full initData string: `query_id=AAEAP2F7...&user=...&auth_date=...&signature=...&hash=...`

## External Services
| Domain | Purpose |
|--------|---------|
| `api.adsgram.ai` | AdsGram ad SDK — serves ads, reports events |
| `backend.tads.me` | TADS SDK bridge — ad assignment (may return `{ads: null}`) |
| `e8ys.com/resolve` | Ad resolution / tracking |
| `play-lh.googleusercontent.com` | Google Play app icons |
| `cdn-mosistorage.akamaized.net` | CDN asset storage |
| `cdn-cgi.r...cloudflareinsights.com` | Cloudflare Web Analytics |

## Headers (Observed on Browser Requests)
```
sec-ch-ua-platform: "Android"
Referer: https://lets.playmonsterland.com/
Origin: https://lets.playmonsterland.com
User-Agent: Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/150.0.7871.181 Mobile Safari/537.36 Telegram-Android/12.9.2.0 (Samsung SM-A5660; Android 16; en_US)
Authorization: tma query_id=AAEAP2F7...&user=...&auth_date=...&signature=...&hash=...
```
Server: `ycalb`  
CORS: `access-control-allow-origin: *`

## Cookies
- `__cf_bm` — Cloudflare Bot Management
- Session/auth cookies passed automatically with requests

---

## Ad Reward Flow (from captured traffic, 2026-08-29)

### Step 1: Create Ad Task (monetag)
```
POST /api/ads/create-task
Content-Type: application/json
Authorization: tma <initData>

{
  "action": "vitals",
  "metadata": { "monsterId": "...", "itemId": "..." }
}
```
**Response (200):**
```json
{
  "success": true,
  "adTxId": "6a92ffe873d66a4df6b05dd6"
}
```

### Step 2: Get SSE Token
```
GET /api/ads/sse-token?txId=<adTxId>
Authorization: tma <initData>
```
**Response (200):** `{ "token": "..." }`

### Step 3: Try TADS SDK Bridge
```
GET https://backend.tads.me/ads_backend?wid=...
```
Returns `{ ads: null, numTeasers: 1, type: "FULLSCREEN_REWARDED" }` — typically no ads from TADS.

### Step 4: Fetch Ad from AdsGram
```
GET https://api.adsgram.ai/adv?blockId=37686&envType=telegram&data_check_string=...&signature=...&raw=bd3e37d9805298e49a38dacd2058742a37fab7888ea1a633d6c6bc8095c87b15
X-Color-Scheme: dark
X-Is-Fullscreen: false
```
Returns `{ blockType: "RewardBlock", banners: [{ banner: { ... } }] }`

### Step 5: Abandon Task
```
POST /api/ads/abandon
Content-Type: application/json
Authorization: tma <initData>

{ "adTxId": "..." }
```
**Response (200):** `{ "abandoned": true }`

### Step 6: Retry with Fallback Provider
If no AdsGram ads or ad failed, create a new task with fallback:
```
POST /api/ads/create-task
Content-Type: application/json
Authorization: tma <initData>

{
  "action": "vitals",
  "metadata": { "monsterId": "...", "itemId": "..." },
  "fallback": true,
  "fallbackOfTxId": "<originalTxId>",
  "lastFailedProvider": "monetag",
  "failedProviders": ["monetag"]
}
```
Retry loop: abandon → create → sse-token → adsgram → abandon → create → ... until ad is available.

### Step 7: Report AdsGram Events
```
GET https://api.adsgram.ai/event?record=<url>&type=render
GET https://api.adsgram.ai/event?record=<url>&type=show
GET https://api.adsgram.ai/event?record=<url>&type=close
```

### Step 8: Claim Reward
```
GET /api/ads/task-result?txId=<adTxId>
Authorization: tma <initData>
```
**Response (200):**
```json
{
  "success": true,
  "newLumis": 43,
  "newVitalValue": 100,
  "userXP": { "xpAwarded": 10, "totalXP": 100 },
  "nextCooldownSeconds": 300
}
```

## Additional Endpoints Observed
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/referral/contest` | Referral contest data |
| POST | `/cdn-cgi/rum` | Cloudflare Web Analytics beacon |
| GET | `backend.tads.me/ads_backend` | TADS SDK bridge |

## Source Data
- Traffic captured from live Mini App session via ADB/CDP on 2026-08-29
- File: `captured_traffic.json` (35 requests, full request/response bodies)
- JS bundle chunks analyzed from `/chunks/` directory
