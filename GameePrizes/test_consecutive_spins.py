import urllib.request
import json
import ssl
import uuid
import gzip
import time

url = "https://api.gamee.com/"
install_uuid = str(uuid.uuid4())
ctx = ssl.create_default_context()

def make_req(payload, token=None):
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
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        raw = resp.read()
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        return json.loads(raw.decode('utf-8'))

print("[1] Registering fresh account...")
reg_res = make_req([{
    "jsonrpc": "2.0",
    "id": "reg",
    "method": "user.authentication.registerAnonymousUser",
    "params": {
        "platform": "app-android",
        "language": "en",
        "country": "US",
        "referralCode": None,
        "metadata": {}
    }
}])[0]

tokens = reg_res["result"]["tokens"]
auth_token = tokens["authenticate"]
refresh_token = tokens["refresh"]
user_id = reg_res["result"]["user"]["id"]
print(f"[+] User {user_id} created! Token: {auth_token[:25]}...")

print("\n[2] Testing consecutive spins without watching ads...")
for spin_num in range(1, 15):
    res = make_req([{
        "jsonrpc": "2.0",
        "id": "spin",
        "method": "luckyGame.spin",
        "params": {"luckyGameId": 62}
    }], auth_token)[0]

    if "error" in res:
        err = res["error"]
        print(f"\n[Spin {spin_num}] STOPPED BY SERVER: code={err.get('code')}, message='{err.get('message')}', reason='{err.get('data', {}).get('reason')}'")
        break

    result = res["result"]
    reward_id = result.get("rewardId")
    rewards = result.get("rewards", [])
    user_state = result.get("luckyGame", {}).get("user", {})
    spin_avail = user_state.get("spinAvailable")
    entry_type = user_state.get("entryType")
    next_period = user_state.get("nextPeriodStart")
    
    # Extract won items
    won_desc = []
    for r in rewards:
        curr = r.get("currency", {}).get("name", "Unknown")
        amt = r.get("amountMicroToken", 0) / 1000000.0
        won_desc.append(f"{amt} {curr}")
    
    # Total balance
    assets = res.get("user", {}).get("assets", [])
    money = next((a["amountMicroToken"]/1000000.0 for a in assets if a.get("currency", {}).get("ticker") == "MONEY"), 0.0)
    tickets = next((a["amountMicroToken"]/1000000.0 for a in assets if a.get("currency", {}).get("ticker") == "TICKET"), 0.0)

    print(f"[Spin {spin_num}] Won: {', '.join(won_desc):<20} | Balance: ${money:.2f}, {int(tickets)} tickets | entryType: {entry_type} | spinAvailable: {spin_avail}")
    time.sleep(1)
