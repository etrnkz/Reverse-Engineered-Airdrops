import urllib.request
import json
import ssl
import uuid
import gzip
import time

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

# Register
reg = req([{
    "jsonrpc": "2.0",
    "id": "reg",
    "method": "user.authentication.registerAnonymousUser",
    "params": {"platform": "app-android", "language": "en", "country": "US", "referralCode": None, "metadata": {}}
}])[0]
token = reg["result"]["tokens"]["authenticate"]
print(f"[+] Account registered, token={token[:20]}...")

# Spin until cap
spins = 0
while True:
    spins += 1
    res = req([{
        "jsonrpc": "2.0",
        "id": "spin",
        "method": "luckyGame.spin",
        "params": {"luckyGameId": 62}
    }], token)[0]
    
    if "error" in res:
        print(f"[-] Spin {spins} stopped: {res['error']['message']}")
        break
    
    rewards = res["result"].get("rewards", [])
    won = ", ".join([f"{r.get('amountMicroToken',0)/1e6} {r.get('currency',{}).get('name')}" for r in rewards])
    print(f"[Spin {spins}] Won: {won}")
    time.sleep(0.5)

print("\n[*] Sending ad.saveAction to simulate watching an ad...")
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
print("[+] ad.saveAction response:", ad_res.get("result"))

print("\n[*] Trying to spin again after ad.saveAction...")
post_ad_spin = req([{
    "jsonrpc": "2.0",
    "id": "spin",
    "method": "luckyGame.spin",
    "params": {"luckyGameId": 62}
}], token)[0]

if "error" in post_ad_spin:
    print("[-] Post-ad spin failed:", post_ad_spin["error"])
else:
    rewards = post_ad_spin["result"].get("rewards", [])
    won = ", ".join([f"{r.get('amountMicroToken',0)/1e6} {r.get('currency',{}).get('name')}" for r in rewards])
    print(f"[+] Post-ad spin SUCCESS: Won {won}!")
