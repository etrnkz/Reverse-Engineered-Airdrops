import urllib.request
import json
import ssl
import uuid
import gzip
import hashlib
import time
from datetime import datetime, timezone

url = "https://api.gamee.com/"
install_uuid = str(uuid.uuid4())
SALT = "oayhu55iu6ktalfafx78u0gjkjsuj0sp9xjmok63"
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
user_id = reg["result"]["user"]["id"]
print(f"[+] User {user_id} registered")

# Play 3 game sessions of Color Hit (ID: 219)
game_id = 219
release_number = 11

for match in range(1, 4):
    print(f"\n[*] Starting Game #{match}...")
    req([{"jsonrpc": "2.0", "id": "start", "method": "game.startGameplay", "params": {"gameId": game_id}}], token)
    
    # Score 120, 25 seconds
    score = 120 * match
    play_time = 25
    run_uuid = str(uuid.uuid4())
    created_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chk_raw = f"{game_id}:{score}:{play_time}:{run_uuid}:{SALT}"
    checksum = hashlib.md5(chk_raw.encode('utf-8')).hexdigest().lower()
    
    save_payload = {
        "gameplayData": {
            "gameId": game_id,
            "releaseNumber": release_number,
            "score": score,
            "playTime": play_time,
            "gameStateData": "",
            "replayVariant": None,
            "replayData": None,
            "createdTime": created_time,
            "metadata": {
                "uuid": install_uuid,
                "id": 1,
                "country": None,
                "language": None
            },
            "section": "home",
            "checksum": checksum,
            "isSaveState": False,
            "gameplayOrigin": "game",
            "completedQuestMissionId": "",
            "questId": 0,
            "questId2": 0,
            "completedGameLevelMissionId": None,
            "uuid": run_uuid,
            "completedGameLevelRewards": None,
            "breakStreak": None,
            "completedAvatarPartId": None
        },
        "location": None
    }
    
    save_res = req([{"jsonrpc": "2.0", "id": "save", "method": "game.saveGameplay", "params": save_payload}], token)[0]
    
    assets = save_res.get("user", {}).get("assets", [])
    tickets = next((a["amountMicroToken"]/1e6 for a in assets if a.get("currency",{}).get("ticker") == "TICKET"), 0.0)
    exp = save_res.get("user", {}).get("progress", {}).get("exp", 0)
    level = save_res.get("user", {}).get("progress", {}).get("level", 1)
    
    print(f"[+] Match #{match} finished! Score: {score} | Tickets: {int(tickets)} | XP: {exp} | Level: {level}")
    time.sleep(1)

# Get full profile
user_data = req([{"jsonrpc": "2.0", "id": "u", "method": "user.get", "params": {}}], token)[0]
profile = user_data.get("result", {}).get("user", {})
gameplays = profile.get("gamee", {}).get("gameplays", 0)
print(f"\n[+] Total gameplays recorded on server: {gameplays}")
