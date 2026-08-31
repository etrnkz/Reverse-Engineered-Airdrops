#!/usr/bin/env node
// MonsterLand Ad Reward Client
// Prompts for initData, auto-runs ad flow, reports balance

const https = require('https');
const { URL } = require('url');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// ─── CONFIG ──────────────────────────────────────────────────────────
const BASE = 'https://lets.playmonsterland.com';
const ADSGRAM_BASE = 'https://api.adsgram.ai';
const BLOCK_ID = 37686;
const USER_AGENT = 'Mozilla/5.0 (Linux; Android 16; K) Telegram-Android/12.9.2.0 (Samsung SM-A075F; Android 16; SDK 36; AVERAGE)';
const MONSTER_ID = '6a6498325ea7188ebd31e186';
const ITEM_ID = 'magic_apple';
const RAW_HASH = 'bd3e37d9805298e49a38dacd2058742a37fab7888ea1a633d6c6bc8095c87b15';

// ─── STATE ───────────────────────────────────────────────────────────
let INIT_DATA = '';

// ─── LOAD AUTH ───────────────────────────────────────────────────────
function loadAuth() {
  // Tokens expire - always prompt user for fresh initData
  return false;
}

// ─── PROMPT ──────────────────────────────────────────────────────────
function promptInitData() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(resolve => {
    rl.question('\n🔥 Paste MonsterLand initData (from tgWebAppData=...):\n> ', (ans) => {
      rl.close();
      resolve(ans.trim());
    });
  });
}

// ─── HTTP ────────────────────────────────────────────────────────────
function request(url, options = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const headers = {
      'User-Agent': USER_AGENT,
      'Referer': 'https://lets.playmonsterland.com/',
      'Origin': 'https://lets.playmonsterland.com',
      'Content-Type': 'application/json',
      ...options.headers,
    };
    if (options.useAuth) headers['Authorization'] = 'tma ' + INIT_DATA;

    const req = https.request({
      hostname: parsed.hostname, port: parsed.port || 443,
      path: parsed.pathname + parsed.search, method: options.method || 'GET', headers,
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const body = Buffer.concat(chunks).toString('utf-8');
        try { resolve({ status: res.statusCode, body: JSON.parse(body) }); }
        catch { resolve({ status: res.statusCode, body }); }
      });
    });
    req.on('error', reject);
    if (options.body) req.write(typeof options.body === 'string' ? options.body : JSON.stringify(options.body));
    req.end();
  });
}

// ─── HELPERS ─────────────────────────────────────────────────────────
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function ts() { return new Date().toISOString().slice(11, 23); }
function log(step, msg, data) {
  console.log(`[${ts()}] [${step}] ${msg}`);
  if (data) console.log(JSON.stringify(data, null, 2));
}
function extractParam(key) {
  const u = new URL(`https://x/?${INIT_DATA}`);
  return u.searchParams.get(key);
}

// ─── API CALLS ───────────────────────────────────────────────────────
async function createTask(fallbackOfTxId = null, lastFailedProvider = null, failedProviders = []) {
  const body = { action: 'vitals', metadata: { monsterId: MONSTER_ID, itemId: ITEM_ID } };
  if (fallbackOfTxId) {
    body.fallback = true;
    body.fallbackOfTxId = fallbackOfTxId;
    body.lastFailedProvider = lastFailedProvider || 'monetag';
    body.failedProviders = failedProviders.length ? failedProviders : ['monetag'];
  }
  const res = await request(`${BASE}/api/ads/create-task`, { method: 'POST', body, useAuth: true });
  log('CREATE', `→ ${res.status}`, res.body);
  return res;
}

async function abandonTask(adTxId) {
  const res = await request(`${BASE}/api/ads/abandon`, { method: 'POST', body: { adTxId }, useAuth: true });
  log('ABANDON', `→ ${res.status}`);
  return res;
}

async function completeTask(adTxId, provider = 'monetag') {
  const res = await request(`${BASE}/api/ads/complete`, { method: 'POST', body: { adTxId, provider }, useAuth: true });
  log('COMPLETE', `→ ${res.status}`);
  return res;
}

async function checkTaskResult(adTxId) {
  const res = await request(`${BASE}/api/ads/task-result?txId=${adTxId}`, { useAuth: true });
  log('TASK-RESULT', `→ ${res.status}`);
  return res;
}

async function sseToken(txId) {
  const res = await request(`${BASE}/api/ads/sse-token?txId=${txId}`, { useAuth: true });
  log('SSE-TOKEN', `→ ${res.status}`);
  return res;
}

async function fetchAdsGramAd() {
  const params = new URLSearchParams({
    envType: 'telegram', blockId: String(BLOCK_ID), platform: 'Linux aarch64',
    language: 'en', top_domain: 'lets.playmonsterland.com', sdk_version: '2.2.1',
    tg_id: '2069970688', tg_platform: 'android', tma_version: '9.6',
    request_id: String(Date.now()), raw: RAW_HASH,
  });
  const authUrl = new URL(`https://placeholder/?${INIT_DATA}`);
  const parts = [];
  for (const k of ['auth_date', 'query_id', 'user']) {
    const v = authUrl.searchParams.get(k);
    if (v) parts.push(`${k}=${v}`);
  }
  params.set('data_check_string', Buffer.from(parts.join('\n')).toString('base64'));
  const sig = authUrl.searchParams.get('signature');
  if (sig) params.set('signature', sig);

  const res = await request(`${ADSGRAM_BASE}/adv?${params}`, {
    method: 'GET', headers: { 'X-Color-Scheme': 'dark', 'X-Is-Fullscreen': 'false' },
  });
  log('ADSGRAM', `→ ${res.status}`, { banners: res.body?.banners?.length });
  return res;
}

async function reportAdsGramEvent(recordUrl) {
  if (!recordUrl) return;
  log('EVENT', `${recordUrl.slice(0, 60)}...`);
  await request(recordUrl, { method: 'GET' });
}

// ─── FLOW ────────────────────────────────────────────────────────────
async function runAdRewardFlow() {
  console.log('\n╔══════════════════════════════════════════════════════════╗');
  console.log('║        MonsterLand Ad Reward Flow v3                   ║');
  console.log('╚══════════════════════════════════════════════════════════╝\n');

  if (!INIT_DATA) {
    console.error('ERROR: No initData. Set MONSTERLAND_INITDATA env var or paste it above.');
    process.exit(1);
  }

  let banner = null;

  // Step 1: Create task (monetag)
  log('FLOW', '── Step 1: Create Task (monetag) ──');
  let createRes = await createTask();
  if (createRes.status === 429 && createRes.body?.waitSeconds) {
    log('WAIT', `Rate limited — waiting ${createRes.body.waitSeconds}s`);
    await sleep(createRes.body.waitSeconds * 1000);
    createRes = await createTask();
  }
  if (!createRes.body?.success || !createRes.body?.adTxId) {
    console.error('❌ Create task failed:', createRes.body);
    return { success: false };
  }
  const txId1 = createRes.body.adTxId;

  // Step 2: SSE token
  log('FLOW', '── Step 2: SSE Token ──');
  await sseToken(txId1);

  // Step 3: Fetch AdsGram ad
  log('FLOW', '── Step 3: Fetch AdsGram Ad ──');
  let adRes = await fetchAdsGramAd();
  if (!adRes.body?.banners?.length) {
    log('ADSGRAM', 'No ads — abandoning & retrying');
    await abandonTask(txId1);
    createRes = await createTask(txId1, 'monetag', ['monetag']);
    if (!createRes.body?.success || !createRes.body?.adTxId) {
      console.error('❌ Retry create-task failed');
      return { success: false };
    }
    const retryTxId = createRes.body.adTxId;
    await sseToken(retryTxId);
    const retryAdRes = await fetchAdsGramAd();
    if (!retryAdRes.body?.banners?.length) {
      await abandonTask(retryTxId);
      const fb2 = await createTask(retryTxId, 'tads', ['monetag', 'tads']);
      if (!fb2.body?.success || !fb2.body?.adTxId) {
        console.error('❌ Second fallback failed');
        return { success: false };
      }
      const txId2 = fb2.body.adTxId;
      await sseToken(txId2);
      const finalAdRes = await fetchAdsGramAd();
      if (!finalAdRes.body?.banners?.length) {
        console.error('❌ No ads on third attempt');
        return { success: false };
      }
      banner = finalAdRes.body.banners[0];
      log('FLOW', `Using fallback txId: ${txId2}`);
    } else {
      banner = retryAdRes.body.banners[0];
      log('FLOW', `Using retry txId: ${retryTxId}`);
    }
  } else {
    banner = adRes.body.banners[0];
  }

  // Step 4: Report AdsGram events
  log('FLOW', '── Step 4: Report AdsGram Events ──');
  if (banner?.banner?.trackings) {
    const renderT = banner.banner.trackings.find(t => t.name === 'render');
    if (renderT) await reportAdsGramEvent(renderT.value);
    await sleep(2000);
    const showT = banner.banner.trackings.find(t => t.name === 'show');
    if (showT) await reportAdsGramEvent(showT.value);
  }

  // Step 5: Abandon & retry with fallback
  log('FLOW', '── Step 5: Abandon & Retry ──');
  await abandonTask(txId1);
  const fbRes = await createTask(txId1, 'monetag', ['monetag']);
  if (!fbRes.body?.success || !fbRes.body?.adTxId) {
    console.error('❌ Fallback create-task failed');
    return { success: false };
  }
  const txId2 = fbRes.body.adTxId;

  await sseToken(txId2);
  const adRes2 = await fetchAdsGramAd();
  if (!adRes2.body?.banners?.length) {
    await abandonTask(txId2);
    const fb2 = await createTask(txId2, 'tads', ['monetag', 'tads']);
    if (!fb2.body?.success || !fb2.body?.adTxId) {
      console.error('❌ Second fallback failed');
      return { success: false };
    }
    const txId3 = fb2.body.adTxId;
    await sseToken(txId3);
    const adRes3 = await fetchAdsGramAd();
    if (!adRes3.body?.banners?.length) {
      console.error('❌ No ads on third attempt');
      return { success: false };
    }
    banner = adRes3.body.banners[0];
  } else {
    banner = adRes2.body.banners[0];
  }

  // Step 6: Report AdsGram events (fallback)
  log('FLOW', '── Step 6: Report AdsGram Events ──');
  if (banner?.banner?.trackings) {
    const renderT2 = banner.banner.trackings.find(t => t.name === 'render');
    if (renderT2) await reportAdsGramEvent(renderT2.value);
    await sleep(2000);
    const showT2 = banner.banner.trackings.find(t => t.name === 'show');
    if (showT2) await reportAdsGramEvent(showT2.value);
  }

  // Step 7: Wait & check result
  log('FLOW', '── Step 7: Wait & Check Result ──');
  await sleep(3000);
  await checkTaskResult(txId2);

  // Step 8: Complete
  log('FLOW', '── Step 8: Create Final Task & Complete ──');
  let finalRes = await createTask();
  if (finalRes.status === 429 && finalRes.body?.waitSeconds) {
    await sleep(finalRes.body.waitSeconds * 1000);
    finalRes = await createTask();
  }
  if (!finalRes.body?.success || !finalRes.body?.adTxId) {
    console.error('❌ Final create-task failed');
    return { success: false };
  }
  const finalTxId = finalRes.body.adTxId;

  let completeRes = await completeTask(finalTxId, 'monetag');
  if (completeRes.status === 429 && completeRes.body?.waitSeconds) {
    await sleep(completeRes.body.waitSeconds * 1000);
    completeRes = await completeTask(txId2, 'adsgram');
  }

  // Result
  console.log('\n╔══════════════════════════════════════════════════════════╗');
  if (completeRes.status === 200 && completeRes.body?.success) {
    console.log('║  ✅ REWARD CLAIMED                                     ║');
    console.log(`║  Lumis:      ${(completeRes.body.newLumis ?? '-').toString().padEnd(33)}║`);
    console.log(`║  Vital:      ${(completeRes.body.newVitalValue ?? '-').toString().padEnd(33)}║`);
    console.log(`║  XP:         +${(completeRes.body.userXP?.xpAwarded ?? 0).toString().padEnd(31)}║`);
    console.log(`║  Cooldown:   ${(completeRes.body.nextCooldownSeconds ?? '-').toString().padEnd(31)}s║`);
  } else {
    console.log('║  ❌ FAILED                                              ║');
    console.log(`║  Status: ${(completeRes.status ?? '-').toString().padEnd(34)}║`);
    console.log(`║  ${JSON.stringify(completeRes.body).slice(0, 55).padEnd(55)}║`);
  }
  console.log('╚══════════════════════════════════════════════════════════╝\n');

  return { success: completeRes.status === 200 && completeRes.body?.success, body: completeRes.body };
}

// ─── CLI ─────────────────────────────────────────────────────────────
async function main() {
  if (process.argv.includes('--help') || process.argv.includes('-h')) {
    console.log(`
MonsterLand Ad Reward Client v3

Usage:
  node ad-reward-client.js
  MONSTERLAND_INITDATA="user=...&auth_date=..." node ad-reward-client.js

Auth:
  - MONSTERLAND_INITDATA env var: Telegram initData string
    Format: "user=<url-encoded JSON>&auth_date=<unix-timestamp>"
  - .auth_token file: same format as MONSTERLAND_INITDATA

Flow: create-task → sse-token → adsgram → abandon → fallback → events → check → complete
`);
    process.exit(0);
  }

  if (!loadAuth()) {
    INIT_DATA = await promptInitData();
    if (!INIT_DATA) {
      console.error('ERROR: No initData provided');
      process.exit(1);
    }
  }

  const result = await runAdRewardFlow();
  process.exit(result.success ? 0 : 1);
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});