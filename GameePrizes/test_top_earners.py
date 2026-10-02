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

res = req([{
    "jsonrpc": "2.0",
    "id": "top",
    "method": "leaderboards.getTopEarners",
    "params": {
        "pagination": {"limit": 20, "offset": 0}
    }
}], token)[0]

print("Top Earners Response:")
print(json.dumps(res, indent=2)[:3000])
