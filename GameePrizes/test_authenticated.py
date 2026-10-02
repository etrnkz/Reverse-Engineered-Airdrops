import urllib.request
import json
import ssl
import gzip

token = "YOUR_TOKEN_HERE"
install_uuid = "YOUR_INSTALL_UUID_HERE"

url = "https://api.gamee.com/"
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
        "id": "luckyGame.getAll",
        "method": "luckyGame.getAll",
        "params": {
            "partnerId": None
        }
    },
    {
        "jsonrpc": "2.0",
        "id": "dailyCheckin.getInformation",
        "method": "dailyCheckin.getInformation",
        "params": {}
    },
    {
        "jsonrpc": "2.0",
        "id": "user.get",
        "method": "user.get",
        "params": {}
    }
]

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method="POST")

ctx = ssl.create_default_context()
try:
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        print("STATUS:", resp.status)
        raw = resp.read()
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        res_json = json.loads(raw.decode('utf-8'))
        print(json.dumps(res_json, indent=2)[:4000])
except Exception as e:
    print("ERROR:", e)
