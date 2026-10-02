import urllib.request
import urllib.error
import json
import ssl
import uuid
import gzip
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

GAMEE_API_URL = "https://api.gamee.com/"
GAME_SCORE_SALT = "oayhu55iu6ktalfafx78u0gjkjsuj0sp9xjmok63"

class GameeClient:
    def __init__(self, token: Optional[str] = None, refresh_token: Optional[str] = None, install_uuid: Optional[str] = None):
        self.install_uuid = install_uuid or str(uuid.uuid4())
        self.token = token
        self.refresh_token = refresh_token
        self.user_id = None
        self.nickname = None
        self.ssl_ctx = ssl.create_default_context()
        self.user_agent = "Gamee/5.18.2.0 (com.gameeapp.android.app; Android 30; mfr Google; mdl Pixel 8a; disp Pixel 8a; res 1080x2400)"

    def _headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Client-Language": "en",
            "X-Install-Uuid": self.install_uuid
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def call(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        data = json.dumps(requests).encode('utf-8')
        req = urllib.request.Request(GAMEE_API_URL, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=20) as resp:
                raw = resp.read()
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
                return json.loads(raw.decode('utf-8'))
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code}: {raw.decode('utf-8')}")

    def call_single(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        res = self.call([{
            "jsonrpc": "2.0",
            "id": method,
            "method": method,
            "params": params or {}
        }])
        if res and isinstance(res, list):
            return res[0]
        return res

    def register_anonymous(self, referral_code: Optional[str] = None) -> Dict[str, Any]:
        resp = self.call_single("user.authentication.registerAnonymousUser", {
            "platform": "app-android",
            "language": "en",
            "country": "US",
            "referralCode": referral_code,
            "metadata": {
                "utm_source": None,
                "utm_medium": None,
                "utm_campaign": None
            }
        })
        result = resp.get("result", {})
        tokens = result.get("tokens", {})
        self.token = tokens.get("authenticate")
        self.refresh_token = tokens.get("refresh")
        user = result.get("user", {})
        self.user_id = user.get("id")
        personal = user.get("personal", {})
        self.nickname = personal.get("nickname")
        
        # Save to local accounts file
        self._save_account_record({
            "user_id": self.user_id,
            "nickname": self.nickname,
            "install_uuid": self.install_uuid,
            "token": self.token,
            "refresh_token": self.refresh_token,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        return result

    def _save_account_record(self, record: Dict[str, Any]):
        import os
        filename = "accounts.json"
        accounts = []
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    accounts = json.load(f)
            except Exception:
                accounts = []
        accounts.append(record)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(accounts, f, indent=2)

    def get_user(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        params = {"userId": user_id} if user_id else {}
        return self.call_single("user.get", params)

    def get_daily_checkin(self) -> Dict[str, Any]:
        return self.call_single("dailyCheckin.getInformation")

    def claim_daily_checkin(self) -> Dict[str, Any]:
        return self.call_single("dailyCheckin.claim")

    def get_lucky_games(self) -> Dict[str, Any]:
        return self.call_single("luckyGame.getAll", {"partnerId": None})

    def spin_wheel(self, lucky_game_id: int = 62) -> Dict[str, Any]:
        return self.call_single("luckyGame.spin", {"luckyGameId": lucky_game_id})

    def watch_ad(self, ad_action: str = "view_to_spin_lucky_game", ad_place: str = "daily-reward", game_id: int = 62) -> Dict[str, Any]:
        """Simulates watching an ad without downloading or rendering any video."""
        return self.call_single("ad.saveAction", {
            "gameId": game_id,
            "adAction": ad_action,
            "adType": "rewarded",
            "adPlace": ad_place,
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
        })

    def spin_all_available(self, lucky_game_id: int = 62, delay_sec: float = 1.0) -> List[Dict[str, Any]]:
        """Spins the wheel repeatedly until the server-side period limit is reached."""
        import time
        results = []
        while True:
            res = self.spin_wheel(lucky_game_id)
            if "error" in res:
                break
            results.append(res.get("result", {}))
            time.sleep(delay_sec)
        return results

    def get_games(self, limit: int = 20, offset: int = 0, sort_type: str = "trending") -> List[Dict[str, Any]]:
        res = self.call_single("game.getAll", {
            "pagination": {"limit": limit, "offset": offset},
            "sortType": sort_type,
            "genreId": None,
            "developerId": None,
            "miniMissionProgress": False,
            "unlockedGames": True
        })
        return res.get("result", {}).get("games", [])

    def start_game(self, game_id: int) -> Dict[str, Any]:
        return self.call_single("game.startGameplay", {"gameId": game_id})

    @staticmethod
    def compute_game_checksum(game_id: int, score: int, play_time_sec: int, run_uuid: str) -> str:
        data = f"{game_id}:{score}:{play_time_sec}:{run_uuid}:{GAME_SCORE_SALT}"
        return hashlib.md5(data.encode('utf-8')).hexdigest().lower()

    def save_gameplay(self, game_id: int, score: int, play_time_sec: int, release_number: int = 0) -> Dict[str, Any]:
        run_uuid = str(uuid.uuid4())
        created_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        checksum = self.compute_game_checksum(game_id, score, play_time_sec, run_uuid)
        
        payload = {
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
                    "uuid": self.install_uuid,
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
        return self.call_single("game.saveGameplay", payload)

    def play_game(self, game_id: int, score: int, play_time_sec: int = 20, release_number: int = 1) -> Dict[str, Any]:
        """Runs a complete start -> save session for a game."""
        self.start_game(game_id)
        return self.save_gameplay(game_id, score, play_time_sec, release_number)

if __name__ == "__main__":
    client = GameeClient()
    print("[*] Registering new anonymous account...")
    reg = client.register_anonymous()
    print(f"[+] User ID: {client.user_id}")
    print(f"[+] Nickname: {client.nickname}")
    print(f"[+] JWT Token: {client.token[:40]}...")

    print("\n[*] Claiming Daily Check-in...")
    try:
        claim = client.claim_daily_checkin()
        rewards = claim.get("result", {}).get("rewards", [])
        print(f"[+] Daily Checkin Result: {rewards}")
    except Exception as e:
        print(f"[-] Checkin error: {e}")

    print("\n[*] Spinning all available Wheel of Fortune turns...")
    spins = client.spin_all_available(62, delay_sec=0.5)
    print(f"[+] Completed {len(spins)} spins!")
    for idx, s in enumerate(spins, 1):
        rewards = s.get("rewards", [])
        won = ", ".join([f"{r.get('amountMicroToken',0)/1e6} {r.get('currency',{}).get('name')}" for r in rewards])
        print(f"    Spin #{idx}: {won}")
    
    user_info = client.get_user()
    assets = user_info.get("user", {}).get("assets", [])
    money = next((a["amountMicroToken"]/1e6 for a in assets if a.get("currency",{}).get("ticker") == "MONEY"), 0.0)
    tickets = next((a["amountMicroToken"]/1e6 for a in assets if a.get("currency",{}).get("ticker") == "TICKET"), 0.0)
    print(f"\n[+] Balance after spins: ${money:.2f} | {int(tickets)} tickets")

    print("\n[*] Playing a game session (Color Hit, ID: 219, score: 250)...")
    try:
        game_res = client.play_game(game_id=219, score=250, play_time_sec=22, release_number=11)
        reward_uuid = game_res.get("result", {}).get("rewardUuid")
        assets = game_res.get("user", {}).get("assets", [])
        tickets = next((a["amountMicroToken"]/1e6 for a in assets if a.get("currency",{}).get("ticker") == "TICKET"), 0.0)
        xp = game_res.get("user", {}).get("progress", {}).get("exp", 0)
        print(f"[+] Score accepted! Reward UUID: {reward_uuid}")
        print(f"[+] Updated Tickets: {int(tickets)} | XP: {xp}")
    except Exception as e:
        print(f"[-] Game error: {e}")
