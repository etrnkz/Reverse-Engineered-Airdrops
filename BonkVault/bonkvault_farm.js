// bonkvault_farm.js — BonkVault game farming script
const https = require('https');

// Config
const FIREBASE_API_KEY = 'AIzaSyD_nS4KFdBPT_esKu4_tSKMI2ClVGxv0Cg';
const API_BASE = 'https://bonkvault.ai.studio';
const TG_ID = process.env.TELEGRAM_ID || '5316914787';

// Helper functions
function httpsPost(url, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const data = JSON.stringify(body);
    const req = https.request({
      hostname: u.hostname, path: u.pathname + u.search, method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data), ...headers }
    }, res => {
      let buf = '';
      res.on('data', c => buf += c);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, data: JSON.parse(buf) }); }
        catch { resolve({ status: res.statusCode, data: buf }); }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function httpsGet(url, headers = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    https.get({ hostname: u.hostname, path: u.pathname + u.search, headers }, res => {
      let buf = '';
      res.on('data', c => buf += c);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, data: JSON.parse(buf) }); }
        catch { resolve({ status: res.statusCode, data: buf }); }
      });
    });
    req.on('error', reject);
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function auth(tgId) {
  const email = `tg_${tgId}@bonkvault.local`;
  const password = `Tg${tgId}!bonkAuth`;
  const res = await httpsPost(
    `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${FIREBASE_API_KEY}`,
    { returnSecureToken: true, email, password, clientType: 'CLIENT_TYPE_WEB' }
  );
  if (!res.data.idToken) throw new Error('Auth failed: ' + JSON.stringify(res.data));
  return {
    uid: res.data.localId,
    token: res.data.idToken,
    headers: { Authorization: `Bearer ${res.data.idToken}` }
  };
}

async function playOnce(headers, uid, game, score) {
  await httpsPost(`${API_BASE}/api/${game}/credit-chance`, { uid }, headers);
  await sleep(300);
  const start = await httpsPost(`${API_BASE}/api/${game}/start-round`, { uid }, headers);
  if (!start.data.success) return { game, error: 'no start', data: start.data };
  await sleep(300);
  const submit = await httpsPost(`${API_BASE}/api/${game}/submit-round`, {
    uid, roundId: start.data.roundId, score
  }, headers);
  return { game, score, roundId: start.data.roundId, ...submit.data };
}

// Main farming function
async function farmCycle(headers, uid, roundsPerGame = 10) {
  const games = ['coin-catcher', 'fruit-ninja', 'candy-match', '2048-mini'];
  const ptsPerRound = { 'coin-catcher': 40, 'fruit-ninja': 45, 'candy-match': 45, '2048-mini': 23 };
  let totalPoints = 0;

  for (const game of games) {
    console.log(`\n--- Farming ${game} (${roundsPerGame} rounds, ~${ptsPerRound[game]} pts/round) ---`);
    let failed = false;
    for (let i = 0; i < roundsPerGame; i++) {
      const result = await playOnce(headers, uid, game, 1000);
      if (result.pointsAwarded) {
        totalPoints += result.pointsAwarded;
        console.log(`  Round ${i + 1}: +${result.pointsAwarded} pts (total: ${totalPoints})`);
      } else {
        console.log(`  Round ${i + 1}: FAILED - ${result.error || JSON.stringify(result)}`);
        failed = true;
        break;
      }
      await sleep(300);
    }
    if (failed) {
      console.log(`  Skipping remaining ${game} rounds due to failure`);
    }
  }

  return totalPoints;
}

// CLI entry point
async function main() {
  const rounds = parseInt(process.argv[2]) || 10;
  console.log(`BonkVault Farm — ${rounds} rounds per game for user ${TG_ID}`);
  console.log('='.repeat(40));

  const authData = await auth(TG_ID);
  console.log(`Auth OK (UID: ${authData.uid})`);

  const totalPoints = await farmCycle(authData.headers, authData.uid, rounds);

  // Get final balance
  const st = await httpsGet(`${API_BASE}/api/coin-catcher/status?uid=${authData.uid}`, authData.headers);
  console.log('\n' + '='.repeat(40));
  console.log(`FARMING COMPLETE — ${totalPoints} points earned`);
  if (st && st.data) {
    console.log(`Coin-catcher chances remaining: ${st.data.chances}`);
  }
}

main().catch(console.error);
