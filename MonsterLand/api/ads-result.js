/**
 * GET /api/ads/result?txId=<task_id>
 * Checks ad task result and credits rewards (Lumis/Vital/XP).
 */

const https = require('https');
const { URL } = require('url');
const fs = require('fs');
const path = require('path');

const BASE = 'https://lets.playmonsterland.com';

let AUTH_TOKEN = '';
let initData = '';
try {
  const token = fs.readFileSync(path.join(__dirname, '..', '.auth_token'), 'utf-8').trim();
  if (token.startsWith('user=')) {
    AUTH_TOKEN = token;
    initData = token;
  }
} catch {}

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

function log(tag, msg) {
  console.log(`[${tag}] ${msg}`);
}

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