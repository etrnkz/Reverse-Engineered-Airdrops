import urllib.request
import json
import ssl
import uuid
import gzip

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

# Register a quick guest token
reg = req([{
    "jsonrpc": "2.0",
    "id": "reg",
    "method": "user.authentication.registerAnonymousUser",
    "params": {"platform": "app-android", "language": "en", "country": "US", "referralCode": None, "metadata": {}}
}])[0]
token = reg["result"]["tokens"]["authenticate"]

# Test batch user.get for 10 sequential IDs around 139657100
batch = []
for uid in range(139657100, 139657110):
    batch.append({
        "jsonrpc": "2.0",
        "id": f"u_{uid}",
        "method": "user.get",
        "params": {"userId": uid}
    })

batch_res = req(batch, token)
print(f"Batch returned {len(batch_res)} responses:")
for item in batch_res:
    res = item.get("result")
    if res:
        uid = res.get("id")
        nick = res.get("personal", {}).get("nickname", "N/A")
        money = res.get("gamee", {}).get("moneyUsdCents", 0) / 100.0
        exp = res.get("gamee", {}).get("experience", 0)
        level = res.get("gamee", {}).get("level", 1)
        gameplays = res.get("gamee", {}).get("gameplays", 0)
        country = res.get("personal", {}).get("countryId", "--")
        print(f"  [ID: {uid}] {nick:<20} | ${money:>6.2f} | Lv.{level} (XP: {exp:>3}) | Plays: {gameplays:>2} | {country}")
    elif "error" in item:
        print(f"  [{item.get('id')}] Error: {item['error']['message']}")
