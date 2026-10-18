# Leaf (`leafearn.site`) Reverse Engineered API & Claim Bot

Automated reward claim loop and gRPC-Web reverse engineered API map for the Leaf (`https://leafearn.site`) Telegram Mini App.

## Features
- **Stateless gRPC-Web Client**: Communicates directly over HTTP/2 using `@connectrpc/connect-web` (`connect-es/2.1.2`) binary protobuf framing.
- **Automated Claim Cycle**: Polling loop for `Sync` → `StartAdView` → `CompleteAdView` (claims reward) → `VerifySafetyCheck`.
- **Zero Heavy Dependencies**: Pure Python standard library + `requests`.

---

## Usage

### 1. Setup
```bash
pip install requests
```

### 2. Run Claim Loop
```bash
python leaf_claim_loop.py
```
When prompted, paste your full Telegram Mini App URL (e.g. `https://leafearn.site/#tgWebAppData=...`) or place it inside `leaf_init_data.txt`.

### 3. Run Diagnostic Probe
```bash
python leaf_probe.py
```

---

## Protocol & Architecture

- **Host**: `https://leafearn.site`
- **Protocol**: gRPC-Web over HTTP/2 (`application/grpc-web+proto`)
- **Binary Framing**:
  - 1 byte compression flag (`0x00`)
  - 4 bytes big-endian length prefix
  - Protobuf payload (empty message = `\x00\x00\x00\x00\x00`)

### Authentication & Headers
Authentication is stateless per-request via Telegram WebApp launch parameters:
- `x-init-data`: Unquoted or URL-encoded `tgWebAppData` string.
- `x-grpc-web`: `1`
- `x-app-rev`: `2135418213`
- `x-user-agent`: `connect-es/2.1.2`
- `x-requested-with`: `org.telegram.plus`

---

## gRPC-Web Service & Method Catalog

| # | Service & Method | Type | Payload | Description |
|---|------------------|------|---------|-------------|
| 1 | `/leaf.v1.AuthService/Sync` | POST | Empty proto | Read-only state check returning user balance, level, and task statuses |
| 2 | `/leaf.v1.TaskService/StartAdView` | POST | Empty proto | Initiates an ad viewing session |
| 3 | `/leaf.v1.TaskService/CompleteAdView` | POST | Empty proto | Completes ad view and credits reward |
| 4 | `/leaf.v1.AuthService/VerifySafetyCheck` | POST | Empty proto | Client safety gate / challenge check |
| 5 | `/leaf.v1.AuthService/SafetyStatus` | POST | Proto payload | Returns safety challenge status |
| 6 | `/leaf.v1.AuthService/SendSafetyCheck` | POST | Proto payload | Submits safety check verification response |
| 7 | `/leaf.v1.ReadService/Tasks` | POST | Proto payload | Lists available social / engagement tasks |

### External Ad Gateways
- `api.adsgram.ai` (Adsgram SDK)
- `d3rem.com` & `adexium.tech` (Bid-request flows)

---

## Files
- `leaf_claim_loop.py` — Main CLI claim-loop automation
- `leaf_probe.py` — gRPC-Web header & view-hint probe
- `.env.example` — Configuration notes
