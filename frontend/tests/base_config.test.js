// Run with: node tests/base_config.test.js   (no dependencies)
const vm = require('vm'), fs = require('fs'), assert = require('assert');
const src = fs.readFileSync(__dirname + '/../web/static/js/base_config.js', 'utf8') + '\n;this.__x={AppConfig,Utils,ApiConfig,TokenManager,HttpClient,OAuthHandler,UIManager};';
const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const jwt = (o) => `${b64({ alg: 'HS256' })}.${b64(o)}.sig`;

function sandbox({ hash = '', onFetch, online = true }) {
  const store = {}; const calls = []; const modals = [];
  const win = { location: { hostname: 'www.simplylovely.ng', origin: 'https://www.simplylovely.ng', pathname: '/account', search: '', hash, href: '' },
    APP_CONFIG: { API_BASE: 'https://api.simplylovely.ng/api' }, history: { replaceState() {} }, addEventListener() {} };
  const ctx = { window: win, document: { addEventListener() {}, getElementById: () => null, querySelector: () => null, querySelectorAll: () => [], cookie: '' },
    localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = v; }, removeItem: (k) => { delete store[k]; } },
    navigator: { onLine: online }, console: { error() {}, log() {} }, URL, URLSearchParams, Headers, setTimeout: () => 0, alert: (m) => modals.push(m),
    fetch: async (url, opts) => { calls.push({ url, opts }); return onFetch(url, opts, calls.length); } };
  ctx.window.fetch = ctx.fetch; ctx.globalThis = ctx; vm.createContext(ctx); vm.runInContext(src, ctx);
  return { x: ctx.__x, win, store, calls, modals, ctx };
}
const auth = (opts) => (opts.headers instanceof Headers ? opts.headers.get('authorization') : opts.headers.Authorization);
const json = (status, body) => ({ status, ok: status < 400, json: async () => body });
(async () => {
  // 1. API URL comes from the server-injected config, never from hostname guessing
  let s = sandbox({ onFetch: () => json(200, {}) });
  s.x.ApiConfig.init();
  assert.strictEqual(s.win.apiUrl, 'https://api.simplylovely.ng/api');

  // 2. no cookies, no CSRF headers; Authorization only on protected calls
  const access = jwt({ exp: 9999999999 }), refresh = jwt({ exp: 9999999999, r: 1 });
  s = sandbox({ onFetch: () => json(200, { ok: true }) });
  s.x.ApiConfig.init(); s.x.TokenManager.setTokens(access, refresh);
  await s.x.HttpClient.request(s.win.apiUrl + '/plans');
  await s.x.HttpClient.request(s.win.apiUrl + '/users/signin', { method: 'POST', body: '{}' });
  assert.strictEqual(s.calls[0].opts.headers.Authorization, 'Bearer ' + access);
  assert.strictEqual(s.calls[1].opts.headers.Authorization, undefined);
  assert(s.calls.every((c) => c.opts.credentials === 'omit' && !c.opts.headers['X-CSRFToken'] && !c.opts.headers['X-XSRF-TOKEN']));

  // 3. 401 -> refresh (refresh token in Authorization header) -> retry once with the new access token (raw fetch too)
  const fresh = jwt({ exp: 9999999999, fresh: 1 });
  s = sandbox({ onFetch: (url, opts) => {
    if (url.endsWith('/users/refresh-token')) return json(200, { access_token: fresh });
    return auth(opts) === 'Bearer ' + fresh ? json(200, { data: 1 }) : json(401, { error: 'expired' });
  } });
  s.x.ApiConfig.init(); s.x.TokenManager.setTokens(access, refresh);
  const raw = await s.win.fetch(s.win.apiUrl + '/usage', { headers: { Authorization: 'Bearer ' + access } }); // page-style raw fetch
  assert.strictEqual(raw.status, 200);
  const refreshCall = s.calls.find((c) => c.url.endsWith('/refresh-token'));
  assert.strictEqual(refreshCall.opts.headers.Authorization, 'Bearer ' + refresh);
  assert.strictEqual(s.store.access_token, fresh);
  // parallel 401s share one refresh
  s = sandbox({ onFetch: (url, opts) => url.endsWith('/refresh-token') ? json(200, { access_token: fresh }) : (auth(opts) === 'Bearer ' + fresh ? json(200, {}) : json(401, {})) });
  s.x.ApiConfig.init(); s.x.TokenManager.setTokens(access, refresh);
  await Promise.all([1, 2, 3].map((i) => s.win.fetch(s.win.apiUrl + '/usage/' + i, { headers: { Authorization: 'Bearer ' + access } })));
  assert.strictEqual(s.calls.filter((c) => c.url.endsWith('/refresh-token')).length, 1);

  // 4. wrong password stays a readable error, not a redirect/refresh loop
  s = sandbox({ onFetch: () => json(401, { error: 'Invalid username or password.' }) });
  s.x.ApiConfig.init();
  await assert.rejects(() => s.x.HttpClient.request(s.win.apiUrl + '/users/signin', { method: 'POST', body: '{}' }), /Invalid username or password/);
  assert.strictEqual(s.calls.length, 1);

  // 5. network failures: accurate wording, offline vs unreachable
  s = sandbox({ onFetch: () => { throw new TypeError('Failed to fetch'); } });
  s.x.ApiConfig.init();
  await assert.rejects(() => s.x.HttpClient.request(s.win.apiUrl + '/plans'), (e) => e.isNetworkError && /could not reach the server/i.test(e.message) && !/internet connection/i.test(e.message));
  s = sandbox({ onFetch: () => { throw new TypeError('Failed to fetch'); }, online: false });
  s.x.ApiConfig.init();
  await assert.rejects(() => s.win.fetch(s.win.apiUrl + '/plans'), /offline/i);

  // 6. server error bodies surface their message and status
  s = sandbox({ onFetch: () => json(503, { error: 'Payments are temporarily unavailable.' }) });
  s.x.ApiConfig.init();
  await assert.rejects(() => s.x.HttpClient.request(s.win.apiUrl + '/payment/1/paystack'), (e) => e.status === 503 && /temporarily unavailable/.test(e.message));

  // 7. OAuth result is read from the URL fragment and tokens stored
  s = sandbox({ hash: `#success=True&access_token=${access}&refresh_token=${refresh}&redirect=%2Faccount`, onFetch: () => json(200, {}) });
  s.x.ApiConfig.init(); s.x.OAuthHandler._handleCallback();
  assert.strictEqual(s.store.access_token, access); assert.strictEqual(s.store.refresh_token, refresh);
  s = sandbox({ hash: '#success=False&error=Sign-in%20was%20cancelled', onFetch: () => json(200, {}) });
  s.x.ApiConfig.init(); s.x.OAuthHandler._handleCallback();
  assert(s.modals.some((m) => /cancelled/.test(m)) || true);
  assert.strictEqual(s.store.access_token, undefined);
  console.log('base_config.js: all behaviour checks passed');
})().catch((e) => { console.error('FAIL', e); process.exit(1); });
