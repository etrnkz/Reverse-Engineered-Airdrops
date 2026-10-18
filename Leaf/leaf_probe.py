"""Leaf (leafearn.site) API probe.

gRPC-Web over HTTP/2, connect-es client, protobuf bodies.
Empty request message = b'\x00\x00\x00\x00\x00'
  (1 byte compression flag + 4 byte big-endian length)

Purpose: find out which headers the server actually ENFORCES, using the
read-only AuthService/Sync call. No state is changed, no reward is claimed.
"""
import os
import sys
import json
import urllib.parse
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "https://leafearn.site/leaf.v1.AuthService/Sync"

def load_init_data():
    if "LEAF_INIT_DATA" in os.environ:
        raw = os.environ["LEAF_INIT_DATA"]
    else:
        candidates = [
            os.path.join(os.path.dirname(__file__), "leaf_init_data.txt"),
            "leaf_init_data.txt",
        ]
        raw = None
        for path in candidates:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read().strip()
                break
        if not raw:
            try:
                raw = input("Enter Leaf tgWebAppData URL or string: ").strip()
            except EOFError:
                pass
    if not raw:
        print("[-] Error: No initData found. Provide LEAF_INIT_DATA env or leaf_init_data.txt")
        sys.exit(1)
    if "tgWebAppData=" in raw:
        data = raw.split("tgWebAppData=", 1)[1].split("&tgWebAppVersion")[0]
        return urllib.parse.unquote(data)
    return raw

INIT = load_init_data()

EMPTY = b"\x00\x00\x00\x00\x00"
# Captured baseline view-hint
VIEW_HINT = ("muiikkbj-bz9ipd."
             "4dbefe13d16a23f32b21d4461c9f8ec4be779e5847696e362b281654cc10141a")

BASE = {
    "content-type": "application/grpc-web+proto",
    "x-grpc-web": "1",
    "x-app-rev": "2135418213",
    "x-user-agent": "connect-es/2.1.2",
    "x-requested-with": "org.telegram.plus",
    "origin": "https://leafearn.site",
    "referer": "https://leafearn.site/",
    "user-agent": ("Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/154.0.8037.57 Mobile "
                   "Safari/537.36 Telegram-Android/12.10.3.0"),
}


def probe(name, extra):
    h = dict(BASE)
    h.update(extra)
    print("\n--- %s ---" % name)
    try:
        r = requests.post(URL, data=EMPTY, headers=h, timeout=25)
        print("HTTP %s  len=%s  ct=%s" % (r.status_code, len(r.content),
                                         r.headers.get("content-type")))
        print("grpc-status: %s" % r.headers.get("grpc-status"))
        if r.headers.get("grpc-message"):
            print("grpc-message: %s" % r.headers["grpc-message"])
        if r.content:
            print("body: %r" % r.content[:120])
        return r
    except Exception as e:
        print("ERROR %s" % e)
        return None


print("init data length:", len(INIT))

# 1. full set, exactly as the app sent it
probe("full headers (baseline, replayed view-hint)", {
    "x-init-data": INIT, "x-view-hint": VIEW_HINT})

# 2. is x-view-hint enforced?
probe("no x-view-hint", {"x-init-data": INIT})

# 3. is x-init-data the real auth?
probe("no x-init-data (keep view-hint)", {"x-view-hint": VIEW_HINT})

# 4. bare minimum
probe("init-data only, minimal headers", {"x-init-data": INIT})
