// bonkvault_all_games.js — Test all 6 games: credit-chance → start-round → submit-round
const https = require('https');

const FIREBASE_API_KEY = 'AIzaSyD_nS4KFdBPT_esKu4_tSKMI2ClVGxv0Cg';
const API_BASE = 'https://bonkvault.ai.studio';
const TG_ID = process.env.TELEGRAM_ID || '5316914787';

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
  return { uid: res.data.localId, token: res.data.idToken, headers: { Authorization: `Bearer ${res.data.idToken}` } };
}

async function playGame(headers, uid, game, score) {
  // 1. Check status
  const status = await httpsGet(`${API_BASE}/api/${game}/status?uid=${uid}`, headers);
  if (!status.data.success) return { game, error: 'status check failed', data: status.data };
  if (status.data.chances === 0) return { game, error: 'no chances', data: status.data };

  // 2. Credit chance (to ensure we have one)
  const credit = await httpsPost(`${API_BASE}/api/${game}/credit-chance`, { uid }, headers);

  // 3. Start round
  const start = await httpsPost(`${API_BASE}/api/${game}/start-round`, { uid }, headers);
  if (!start.data.success || !start.data.roundId) return { game, error: 'start-round failed', data: start.data };

  // 4. Submit round
  const submit = await httpsPost(`${API_BASE}/api/${game}/submit-round`, {
    uid,
    roundId: start.data.roundId,
    score
  }, headers);

  return {
    game,
    roundId: start.data.roundId,
    duration: start.data.durationSeconds,
    score,
    submitStatus: submit.status,
    submitData: submit.data
  };
}

async function main() {
  const { uid, headers } = await auth(TG_ID);
  console.log(`Auth OK (UID: ${uid})\n`);

  // Games with their starting chances
  const games = ['coin-catcher', 'fruit-ninja', 'candy-match', 'word-game', '2048-mini', 'quick-quiz'];
  const results = [];

  // First: credit chances for all games
  console.log('=== Crediting chances for all games ===');
  for (const g of games) {
    const res = await httpsPost(`${API_BASE}/api/${g}/credit-chance`, { uid }, headers);
    console.log(`${g} credit-chance: ${res.status} ${JSON.stringify(res.data)}`);
    await sleep(300);
  }

  // Then: play each game with different scores to test point correlation
  console.log('\n=== Playing all games ===');
  const scores = [100, 200, 500, 1000]; // Test different scores
  let scoreIdx = 0;

  for (const g of games) {
    const score = scores[scoreIdx % scores.length];
    scoreIdx++;
    const result = await playGame(headers, uid, g, score);
    results.push(result);
    console.log(`${g} (score ${score}): ${JSON.stringify(result)}`);
    await sleep(500);
  }

  // Check final balances
  console.log('\n=== Final Status ===');
  for (const g of games) {
    const res = await httpsGet(`${API_BASE}/api/${g}/status?uid=${uid}`, headers);
    console.log(`${g}: ${JSON.stringify(res.data)}`);
  }

  // Check user profile for balance
  console.log('\n=== User Profile ===');
  const profile = await httpsGet(`${API_BASE}/api/user/profile?uid=${uid}`, headers);
  console.log(`profile: ${JSON.stringify(profile.data)}`);

  console.log('\n=== Summary ===');
  for (const r of results) {
    if (r.submitData && r.submitData.success) {
      console.log(`${r.game}: score=${r.score}, points=${r.submitData.pointsAwarded}, balance=${r.submitData.newBalance}`);
    } else {
      console.log(`${r.game}: FAILED - ${r.error || JSON.stringify(r.submitData)}`);
    }
  }
}

main().catch(console.error);
