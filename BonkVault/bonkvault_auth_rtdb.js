/**
 * BonkVault Auth + RTDB Explorer
 * 
 * Step 1: Register + authenticate with Firebase REST API (no browser needed)
 * Step 2: Read Firebase RTDB to understand user data structure
 * Step 3: Explore RTDB paths for game data
 */

const https = require('https');

const FIREBASE_API_KEY = 'AIzaSyD_nS4KFdBPT_esKu4_tSKMI2ClVGxv0Cg';
const BONKVAULT_HOST = 'bonkvault.ai.studio';

// Configurable User
const TG_ID = process.env.TELEGRAM_ID || '5316914787';
const USER = {
  id: TG_ID,
  username: process.env.TELEGRAM_USERNAME || 'reverserguy',
  firstName: process.env.TELEGRAM_FIRST_NAME || 'Player',
};

function httpsRequest(url, options = {}, body = null) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const req = https.request({
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'POST',
      headers: options.headers || {},
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, data: JSON.parse(data), raw: data }); }
        catch { resolve({ status: res.statusCode, data: null, raw: data }); }
      });
    });
    req.on('error', reject);
    if (body) req.write(typeof body === 'string' ? body : JSON.stringify(body));
    req.end();
  });
}

async function main() {
  console.log(`=== Step 1: Register User (${USER.id}) ===`);
  const regResp = await httpsRequest(`https://${BONKVAULT_HOST}/api/telegram/register-user`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  }, { id: USER.id, username: USER.username, firstName: USER.firstName });
  console.log(`Status: ${regResp.status}`);
  console.log(`Response:`, JSON.stringify(regResp.data, null, 2));

  console.log('\n=== Step 2: Firebase signInWithPassword ===');
  const email = `tg_${USER.id}@bonkvault.local`;
  const password = `Tg${USER.id}!bonkAuth`;
  console.log(`Email: ${email}`);

  const signInResp = await httpsRequest(
    `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${FIREBASE_API_KEY}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    },
    {
      returnSecureToken: true,
      email,
      password,
      clientType: 'CLIENT_TYPE_WEB',
    }
  );
  console.log(`Status: ${signInResp.status}`);
  if (signInResp.status !== 200) {
    console.log('Raw:', signInResp.raw?.substring(0, 500));
    // Try creating the account first
    console.log('\n--- Account may not exist, trying signUp ---');
    const signUpResp = await httpsRequest(
      `https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=${FIREBASE_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      },
      {
        returnSecureToken: true,
        email,
        password,
        clientType: 'CLIENT_TYPE_WEB',
      }
    );
    console.log(`SignUp Status: ${signUpResp.status}`);
    console.log(`SignUp Response:`, JSON.stringify(signUpResp.data, null, 2));
    if (signUpResp.status === 200) {
      // Now sign in
      const signIn2 = await httpsRequest(
        `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${FIREBASE_API_KEY}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        },
        {
          returnSecureToken: true,
          email,
          password,
          clientType: 'CLIENT_TYPE_WEB',
        }
      );
      console.log(`\nRe-signIn Status: ${signIn2.status}`);
      Object.assign(signInResp, signIn2);
    }
  }

  if (!signInResp.data || !signInResp.data.idToken) {
    console.log('FAILED to get idToken. Raw:', signInResp.raw?.substring(0, 500));
    return;
  }

  const idToken = signInResp.data.idToken;
  const localId = signInResp.data.localId;
  console.log(`\nlocalId: ${localId}`);
  console.log(`idToken: ${idToken.substring(0, 60)}...`);

  console.log('\n=== Step 3: Verify token via accounts:lookup ===');
  const lookupResp = await httpsRequest(
    `https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=${FIREBASE_API_KEY}`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' } },
    { idToken }
  );
  console.log(`Status: ${lookupResp.status}`);
  console.log(`Users:`, JSON.stringify(lookupResp.data?.users?.map(u => ({
    localId: u.localId,
    email: u.email,
    createdAt: u.createdAt,
    lastLoginAt: u.lastLoginAt,
  })), null, 2));

  console.log('\n=== Step 4: Read Firebase RTDB - User Profile ===');
  const rtdbBase = 'https://bonkvault-e1924-default-rtdb.firebaseio.com';
  
  // Try reading the user's data at users/{localId}
  const userPath = `/users/${localId}.json`;
  const userResp = await httpsRequest(
    `${rtdbBase}${userPath}?auth=${idToken}`,
    { method: 'GET', headers: {} }
  );
  console.log(`Path: users/${localId}`);
  console.log(`Status: ${userResp.status}`);
  console.log(`Data:`, userResp.raw?.substring(0, 2000));

  // Try other common paths
  const pathsToTry = [
    '/users.json',
    '/games.json',
    '/bonk.json',
    '/wallet.json',
    '/rewards.json',
    '/inventory.json',
    '/upgrades.json',
    '/stats.json',
    '/config.json',
    '/leaderboard.json',
    '/referrals.json',
  ];

  console.log('\n=== Step 5: Explore RTDB root paths ===');
  for (const path of pathsToTry) {
    const resp = await httpsRequest(
      `${rtdbBase}${path}?auth=${idToken}&shallow=true`,
      { method: 'GET', headers: {} }
    );
    const preview = resp.raw?.substring(0, 200) || '';
    if (resp.status === 200 && preview !== 'null') {
      console.log(`✓ ${path} → ${resp.status}: ${preview}`);
    } else {
      console.log(`✗ ${path} → ${resp.status}: ${preview}`);
    }
  }

  // Also try reading root
  console.log('\n=== Step 6: Read RTDB root ===');
  const rootResp = await httpsRequest(
    `${rtdbBase}/.json?auth=${idToken}`,
    { method: 'GET', headers: {} }
  );
  console.log(`Status: ${rootResp.status}`);
  console.log(`Root data (first 3000 chars):`, rootResp.raw?.substring(0, 3000));
}

main().catch(console.error);
