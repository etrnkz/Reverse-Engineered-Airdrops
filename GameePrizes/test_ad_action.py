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

reg = req([{
    "jsonrpc": "2.0",
    "id": "reg",
    "method": "user.authentication.registerAnonymousUser",
    "params": {"platform": "app-android", "language": "en", "country": "US", "referralCode": None, "metadata": {}}
}])[0]

token = reg["result"]["tokens"]["authenticate"]
print(f"[+] Account registered, token={token[:20]}...")

ad_res = req([{
    "jsonrpc": "2.0",
    "id": "ad.saveAction",
    "method": "ad.saveAction",
    "params": {
        "gameId": 62,
        "adAction": "view_to_spin_lucky_game",
        "adType": "rewarded",
        "adPlace": "daily-reward",
        "adNetwork": "AppLovin",
        "ticketsCount": 0,
        "ticketMultiplier": 1.0,
        "adUnavailable": False,
        "miningEventId": None,
        "uuid": str(uuid.uuid4()),
        "multiplier": None,
        "adRevenue": 0.02,
        "adEcpm": 20.0,
        "adCount": None,
        "adDisabled": False,
        "adId": None,
        "platform": "app-android"
    }
}], token)[0]

print("\nad.saveAction Response:")
print(json.dumps(ad_res, indent=2))
