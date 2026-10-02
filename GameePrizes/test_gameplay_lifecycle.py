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

print("[1] Registering fresh account...")
reg = req([{
    "jsonrpc": "2.0",
    "id": "reg",
    "method": "user.authentication.registerAnonymousUser",
    "params": {"platform": "app-android", "language": "en", "country": "US", "referralCode": None, "metadata": {}}
}])[0]
token = reg["result"]["tokens"]["authenticate"]
user_id = reg["result"]["user"]["id"]
print(f"[+] Account registered (User ID {user_id})")

# Game: Color Hit (ID: 219, Release: 11)
game_id = 219
release_number = 11

print(f"\n[2] Starting gameplay session for Game ID {game_id} (Color Hit)...")
start_res = req([{
    "jsonrpc": "2.0",
    "id": "start",
    "method": "game.startGameplay",
    "params": {"gameId": game_id}
}], token)[0]
print("[+] Start response:", json.dumps(start_res, indent=2)[:300])

score = 65
play_time_sec = 18
run_uuid = str(uuid.uuid4())
created_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Compute checksum: md5(f"{gameId}:{score}:{playTime}:{uuid}:{SALT}")
chk_raw = f"{game_id}:{score}:{play_time_sec}:{run_uuid}:{SALT}"
checksum = hashlib.md5(chk_raw.encode('utf-8')).hexdigest().lower()
print(f"\n[3] Submitting score={score}, playTime={play_time_sec}s, checksum={checksum}...")

save_payload = {
    "gameplayData": {
        "gameId": game_id,
        "releaseNumber": release_number,
        "score": score,
        "playTime": play_time_sec,
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

save_res = req([{
    "jsonrpc": "2.0",
    "id": "save",
    "method": "game.saveGameplay",
    "params": save_payload
}], token)[0]

print("\n--- SAVE GAMEPLAY RESULT ---")
print(json.dumps(save_res, indent=2))
