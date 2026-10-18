#!/usr/bin/env python3
"""
leaf_claim_loop.py — automated claim-loop for Leaf (leafearn.site) mini-app.

Poll-replay the gRPC-Web endpoint cycle that triggers reward credits:
  Sync      → StartAdView → CompleteAdView → (optional) VerifySafetyCheck
The loop repeats until manually stopped or balance is exhausted.

Dependencies: requests (STDLIB only, no extra packages needed).
Usage:
    python leaf_claim_loop.py
    — prompted for the Telegram Mini App URL once at start.
    — loop runs stake-30–style claim cycles; each iteration attempts one
      full reward claim (ad view start → complete → safety check → credit).
"""

import json, os, re, sys, time, urllib.error, urllib.parse
import requests

# ──────────────────────────────────────────────────────────────
# Configuration / bootstrap
# ──────────────────────────────────────────────────────────────

BASE_URL = "https://leafearn.site"

# gRPC-Web headers that the real app uses (from captured HAR)
GRPC_HEADERS = {
    "content-type": "application/grpc-web+proto",
    "x-grpc-web": "1",
    "x-app-rev": "2135418213",
    "x-user-agent": "connect-es/2.1.2",
    "x-requested-with": "org.telegram.plus",
    "origin": "https://leafearn.site",
    "referer": "https://leafearn.site/",
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/154.0.8037.57 Mobile "
        "Safari/537.36 Telegram-Android/12.10.3.0"
    ),
}


def extract_init_data(url_input):
    """Same extractor used by ludo_bot.py — normalises mixed encoding."""
    s = url_input.strip()
    if "tgWebAppData=" in s:
        m = re.search(r"tgWebAppData=(.*?)(?:&tgWebAppVersion=|$)", s, re.S)
        data = m.group(1) if m else s.split("tgWebAppData=", 1)[1]
    elif "initData=" in s:
        data = s.split("initData=", 1)[1].split("&tgWebAppVersion=")[0].strip()
    else:
        return s
    # Normalise in a loop (single, mixed, double encoding):
    # if the user value still holds %25xx, one unquote pass; otherwise
    # decode outer separators only. Never touch inner %XX (user JSON must stay encoded).
    for _ in range(4):
        um = re.search(r"user(?:=|%3[Dd]|%253[Dd])([^&]*)", data)
        if um and "%25" in um.group(1):
            data = urllib.parse.unquote(data)
            continue
        nd = data.replace("%3D", "=").replace("%3d", "=").replace("%26", "&")
        if nd == data:
            return data
        data = nd
    return data


def get_init_data():
    print("Paste your Telegram Mini App URL (or press ENTER to skip):")
    print("  e.g. https://leafearn.site/#tgWebAppData=...") 
    try:
        url_input = input("\n> ").strip()
    except EOFError:
        print("[-] No URL provided.")
        sys.exit(1)
    if not url_input:
        # Try reading from known fallback location
        fallback = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "leaf_init_data.txt"
        )
        if os.path.exists(fallback):
            print(f"[+] Reading initData from {fallback}")
            with open(fallback, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            return extract_init_data(raw)
        print(
            "[-] No URL provided and no fallback file found. "
            "Create leaf_init_data.txt with a full tgWebAppData URL "
            "or paste the URL when prompted."
        )
        sys.exit(1)
    init_data = extract_init_data(url_input)
    if not init_data or "hash=" not in init_data:
        print("[-] Failed to extract initData. Make sure you paste the full URL.")
        sys.exit(1)
    print("[+] Extracted initData (%d chars)" % len(init_data))
    # persist for future runs
    try:
        with open(fallback, "w", encoding="utf-8") as f:
            f.write("tgWebAppData=" + init_data)
        print(f"[+] Saved initData to {fallback}")
    except Exception:
        pass
    return init_data


# ──────────────────────────────────────────────────────────────
# gRPC-Web helper
# ──────────────────────────────────────────────────────────────

EMPTY_GRPC = b"\x00\x00\x00\x00\x00"  # 1-byte flag + 4-byte big-endian length (0)


def grpc_post(path, init_data, extra_headers=None):
    """POST a gRPC-Web request (empty body) and return the response."""
    url = BASE_URL + path
    headers = dict(GRPC_HEADERS)
    headers["x-init-data"] = init_data.encode("utf-8").decode("latin-1")
    if extra_headers:
        headers.update(extra_headers)
    try:
        r = requests.post(url, data=EMPTY_GRPC, headers=headers, timeout=25)
        return r
    except Exception as e:
        print("[-] network error %s %s: %s" % (path, url, e))
        return None


# ──────────────────────────────────────────────────────────────
# Leaf API cycle
# ──────────────────────────────────────────────────────────────

def api_sync(init_data):
    """Sync — no-op read-only call that returns current state."""
    r = grpc_post("/leaf.v1.AuthService/Sync", init_data)
    if not r:
        return None
    print("  Sync HTTP %s  gRPC-status=%s" % (r.status_code, r.headers.get("grpc-status")))
    if r.headers.get("grpc-message"):
        print("  grpc-message: %s" % r.headers["grpc-message"])
    if r.content:
        # try pretty-print first few bytes
        try:
            preview = r.content[:200].decode("utf-8", errors="replace")
        except Exception:
            preview = r.content[:200].hex()
        print("  body (first 200): %s" % preview)
    return r


def api_start_ad_view(init_data):
    """StartAdView — begin an ad view session."""
    r = grpc_post("/leaf.v1.TaskService/StartAdView", init_data)
    if not r:
        return None
    print("  StartAdView HTTP %s  gRPC-status=%s" % (r.status_code, r.headers.get("grpc-status")))
    if r.headers.get("grpc-message"):
        print("  grpc-message: %s" % r.headers["grpc-message"])
    if r.content:
        try:
            preview = r.content[:200].decode("utf-8", errors="replace")
        except Exception:
            preview = r.content[:200].hex()
        print("  body (first 200): %s" % preview)
    return r


def api_complete_ad_view(init_data):
    """CompleteAdView — finish the ad view and claim the reward."""
    r = grpc_post("/leaf.v1.TaskService/CompleteAdView", init_data)
    if not r:
        return None
    print("  CompleteAdView HTTP %s  gRPC-status=%s" % (r.status_code, r.headers.get("grpc-status")))
    if r.headers.get("grpc-message"):
        print("  grpc-message: %s" % r.headers["grpc-message"])
    if r.content:
        try:
            text = r.content.decode("utf-8", errors="replace")[:500]
        except Exception:
            text = r.content[:500].hex()
        print("  body (first 500): %s" % text)
    return r


def api_verify_safety_check(init_data):
    """VerifySafetyCheck — safety-gate check (may be optional)."""
    r = grpc_post("/leaf.v1.AuthService/VerifySafetyCheck", init_data)
    if not r:
        return None
    print("  VerifySafetyCheck HTTP %s  gRPC-status=%s" % (r.status_code, r.headers.get("grpc-status")))
    if r.headers.get("grpc-message"):
        print("  grpc-message: %s" % r.headers["grpc-message"])
    if r.content:
        try:
            preview = r.content[:200].decode("utf-8", errors="replace")
        except Exception:
            preview = r.content[:200].hex()
        print("  body (first 200): %s" % preview)
    return r


# ──────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────

def main():
    init_data = get_init_data()
    cycle = 0
    success = 0
    fail = 0
    try:
        while True:
            cycle += 1
            print("\n=== claim loop cycle %d ===" % cycle)

            # 1) Sync
            print("[1/4] Sync...")
            sync_r = api_sync(init_data)
            if not sync_r or sync_r.status_code != 200:
                print("  ! Sync failed, stopping cycle.")
                fail += 1
                time.sleep(3)
                continue

            # 2) StartAdView
            print("[2/4] StartAdView...")
            start_r = api_start_ad_view(init_data)
            if not start_r or start_r.status_code != 200:
                print("  ! StartAdView failed, skipping complete.")
                fail += 1
                time.sleep(3)
                continue

            # 3) CompleteAdView (claim reward)
            print("[3/4] CompleteAdView (claim reward)...")
            complete_r = api_complete_ad_view(init_data)
            if not complete_r or complete_r.status_code != 200:
                print("  ! CompleteAdView failed.")
                fail += 1
                time.sleep(3)
                continue

            # 4) Optional VerifySafetyCheck
            print("[4/4] VerifySafetyCheck...")
            verify_r = api_verify_safety_check(init_data)
            if verify_r and verify_r.status_code != 200:
                print("  ! VerifySafetyCheck failed (non-fatal).")
                # not stopping the loop — safety check may be optional

            success += 1
            print("  ✅ cycle %d completed (success %d / fail %d)" % (cycle, success, fail))
            # cool-down between cycles so we don't hammer the server
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n[–] claim loop stopped by user after %d cycles" % cycle)
        print("  total success: %d | total fail: %d" % (success, fail))


if __name__ == "__main__":
    main()