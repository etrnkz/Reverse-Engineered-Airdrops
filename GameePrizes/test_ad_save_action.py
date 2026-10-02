import urllib.request
import json
import ssl
import uuid
import gzip

token = "YOUR_TOKEN_HERE"
install_uuid = "YOUR_INSTALL_UUID_HERE"

url = "https://api.gamee.com/"
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

payload = [
    {
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
    }
]

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        raw = resp.read()
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        res_json = json.loads(raw.decode('utf-8'))
        print("AD SAVE ACTION RESPONSE:")
        print(json.dumps(res_json, indent=2))
except Exception as e:
    print("ERROR:", e)
