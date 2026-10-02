import urllib.request
import json
import ssl
import uuid
import gzip

install_uuid = str(uuid.uuid4())

url = "https://api.gamee.com/"
headers = {
    "User-Agent": "Gamee/5.18.2.0 (com.gameeapp.android.app; Android 30; mfr Google; mdl Pixel 8a; disp Pixel 8a; res 1080x2400)",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Client-Language": "en",
    "X-Install-Uuid": install_uuid
}

payload = [
    {
        "jsonrpc": "2.0",
        "id": "user.authentication.registerAnonymousUser",
        "method": "user.authentication.registerAnonymousUser",
        "params": {
            "platform": "app-android",
            "language": "en",
            "country": "US",
            "referralCode": None,
            "metadata": {
                "utm_source": None,
                "utm_medium": None,
                "utm_campaign": None
            }
        }
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
        print(json.dumps(res_json, indent=2))
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    body = e.read()
    try:
        body = gzip.decompress(body)
    except Exception:
        pass
    print("BODY:", body.decode('utf-8'))
except Exception as e:
    print("ERROR:", e)
