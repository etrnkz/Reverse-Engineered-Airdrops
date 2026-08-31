/**
 * POST /api/ads/create
 * Creates an ad task for the user.
 * Receives initData from bot, forwards to ad APIs, returns task ID.
 */

const https = require('https');
const { URL } = require('url');
const fs = require('fs');
const path = require('path');

const BASE = 'https://lets.playmonsterland.com';
const ADSGRAM_BASE = 'https://api.adsgram.ai';
const BLOCK_ID = 37686;
const MONSTER_ID = '6a6498325ea7188ebd31e186';
const ITEM_ID = 'magic_apple';

let AUTH_TOKEN = '';
let INIT_DATA_OVERRIDE = process.env.MONSTERLAND_INITDATA;

// Try to read auth token from .auth_token file
try {
  const token = fs.readFileSync(path.join(__dirname, '..', '.auth_token'), 'utf-8').trim();
  if (token.startsWith('user=')) {
    AUTH_TOKEN = token;
  }
} catch {}

function pathJoin(...segments) {
  return segments.reduce((a, b) => a ? a + '/' + b : b, '');
}

function request(options) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(options.url);
    const opts = {
      hostname: parsed.hostname,
      port: parsed.port || 443,
      path: parsed.pathname + parsed.search,
      method: options.method || 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 16; K) Telegram-Android/12.9.2.0 (Samsung SM-A075F; Android 16; SDK 36; AVERAGE)',
        'Referer': 'https://lets.playmonsterland.com/',
        'sec-ch-ua-platform': '"Android"',
        'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Android WebView";v="150"',
        'sec-ch-ua-mobile': '?1',
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    const req = https.request(opts, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const body = Buffer.concat(chunks).toString('utf-8');
        try {
          resolve({ status: res.statusCode, headers: res.headers, body: JSON.parse(body) });
        } catch {
          resolve({ status: res.statusCode, headers: res.headers, body });
        }
      });
    });

    req.on('error', reject);
    if (options.body != null) {
      const bodyStr = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
      req.write(bodyStr);
    }
    req.end();
  });
}

exports.create = async (req, res) => {
  try {
    // Get initData from query params or body
    let initData = '';
    if (req.query && req.query.initData) {
      initData = req.query.initData;
    } else if (req.body && req.body.initData) {
      initData = req.body.initData;
    } else if (req.headers['x-init-data']) {
      initData = req.headers['x-init-data'];
    }

    if (!initData) {
      return res.status(400).json({ success: false, error: 'Missing initData' });
    }

    // Step 1: Create task with monetag
    const monetagBody = {
      action: 'vitals',
      metadata: { monsterId: MONSTER_ID, itemId: ITEM_ID },
    };

    const monetagUrl = new URL(`${BASE}/api/ads/create-task`);
    monetagUrl.search = initData; // Append initData as query params

    log('CREATE', `POST /api/ads/create-task [provider=monetag]`);

    let monetagRes;
    try {
      monetagRes = await request({
        method: 'POST',
        url: monetagUrl.toString(),
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(monetagBody),
      });
    } catch (e) {
      monetagRes = { status: 0, body: { success: false, error: 'monetag request failed' } };
    }

    log('CREATE', `→ ${monetagRes.status}`, monetagRes.body);

    if (!monetagRes.body?.success || !monetagRes.body?.adTxId) {
      // Fallback to adsgram if monetag fails
      log('FALLBACK', 'monetag failed, trying adsgram...');

      const adsgramParams = new URLSearchParams({
        envType: 'telegram',
        blockId: String(BLOCK_ID),
        platform: 'Linux aarch64',
        language: 'en',
        top_domain: 'lets.playmonsterland.com',
        sdk_version: '2.2.1',
        tg_id: '2069970688',
        tg_platform: 'android',
        tma_version: '9.6',
        request_id: String(Date.now()),
      });

      // Add data_check_string and signature from initData
      try {
        const authUrl = new URL(`https://placeholder/?${initData}`);
        const parts = [];
        for (const k of ['auth_date', 'query_id', 'user']) {
          const v = authUrl.searchParams.get(k);
          if (v) parts.push(`${k}=${v}`);
        }
        adsgramParams.set('data_check_string', Buffer.from(parts.join('\n')).toString('base64'));
        const sig = authUrl.searchParams.get('signature');
        if (sig) adsgramParams.set('signature', sig);
      } catch {}

      const adsgramUrl = new URL(`${ADSGRAM_BASE}/adv`);
      adsgramUrl.search = adsgramParams.toString();

      log('ADSGRAM', `GET /adv [blockId=${BLOCK_ID}]`);
      let adsgramRes;
      try {
        adsgramRes = await request({
          method: 'GET',
          url: adsgramUrl.toString(),
          headers: { 'X-Color-Scheme': 'dark', 'X-Is-Fullscreen': 'false' },
        });
      } catch (e) {
        adsgramRes = { status: 0, body: { error: 'adsgram request failed' } };
      }

      log('ADSGRAM', `→ ${adsgramRes.status}`, typeof adsgramRes.body === 'object' && adsgramRes.body !== null ? { blockType: adsgramRes.body.blockType, bannerCount: adsgramRes.body.banners?.length } : adsgramRes.body);

      if (!adsgramRes.body?.banners?.length) {
        return res.status(200).json({ 
          success: false, 
          error: 'no ads available',
          fallback: true 
        });
      }

      const banner = adsgramRes.body.banners[0];
      const txId = `adsgram_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      return res.status(200).json({ 
        success: true, 
        adTxId: txId,
        provider: 'adsgram',
        banner: {
          title: banner.banner.bannerAssets?.find(a => a.name === 'title')?.value || 'ad',
          tracking: banner.banner.trackings || []
        }
      });
    }

    const txId1 = monetagRes.body.adTxId;
    log('FLOW', `monetag txId: ${txId1}`);

    // Step 2: Abandon monetag task
    await abandonTask(txId1);

    // Step 3: Create adsgram fallback task
    const fallbackBody = {
      action: 'vitals',
      metadata: { monsterId: MONSTER_ID, itemId: ITEM_ID },
      fallback: true,
      fallbackOfTxId: txId1,
      lastFailedProvider: 'monetag',
      failedProviders: ['monetag'],
    };

    const fallbackUrl = new URL(`${BASE}/api/ads/create-task?fallback=true`);
    fallbackUrl.search = initData;

    log('FALLBACK-CREATE', `POST /api/ads/create-task [provider=adsgram]`);
    let fallbackRes;
    try {
      fallbackRes = await request({
        method: 'POST',
        url: fallbackUrl.toString(),
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fallbackBody),
      });
    } catch (e) {
      fallbackRes = { status: 0, body: { success: false, error: 'fallback create-task failed' } };
    }

    log('FALLBACK-CREATE', `→ ${fallbackRes.status}`, fallbackRes.body);

    if (!fallbackRes.body?.success || !fallbackRes.body?.adTxId) {
      return res.status(200).json({ 
        success: false, 
        error: 'fallback create-task failed',
        monetagTxId: txId1 
      });
    }

    const txId2 = fallbackRes.body.adTxId;
    log('FLOW', `adsgram txId: ${txId2}`);

    // Step 4: Report AdsGram events (from the fetched ad)
    // We need to get the ad first - but for the create endpoint,
    // we'll just return the task ID and let the client handle reporting

    res.status(200).json({ 
      success: true, 
      adTxId: txId2,
      provider: 'adsgram',
      monetagTxId: txId1 
    });

  } catch (err) {
    console.error('ADS CREATE ERROR:', err);
    res.status(500).json({ success: false, error: err.message });
  }
};

exports.result = async (req, res) => {
  try {
    const { txId } = req.query;

    if (!txId) {
      return res.status(400).json({ success: false, error: 'Missing txId' });
    }

    const resultUrl = new URL(`${BASE}/api/ads/task-result`);
    resultUrl.search = initData;
    resultUrl.searchParams.set('txId', txId);

    log('TASK-RESULT', `GET /api/ads/task-result?txId=${txId}`);
    const result = await request({
      method: 'GET',
      url: resultUrl.toString(),
      headers: { 'Content-Type': 'application/json' },
    });

    res.status(200).json(result.body || result);

  } catch (err) {
    console.error('ADS RESULT ERROR:', err);
    res.status(500).json({ success: false, error: err.message });
  }
};

function abandonTask(adTxId) {
  const abandonUrl = new URL(`${BASE}/api/ads/abandon`);
  abandonUrl.search = initData;
  log('ABANDON', `POST /api/ads/abandon [txId=${adTxId}]`);
  return request({
    method: 'POST',
    url: abandonUrl.toString(),
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ adTxId }),
  });
}