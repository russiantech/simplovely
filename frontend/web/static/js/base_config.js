/**
 * base_config.js — Single authoritative application bootstrap
 *
 * Defines:
 *   AppConfig    — compile-time constants
 *   Utils        — pure helpers (storage, cookie, string)
 *   ApiConfig    — API URL detection + init
 *   TokenManager — access/refresh token lifecycle
 *   HttpClient   — fetch wrapper with auto-refresh + user-friendly errors
 *   UIManager    — response_modal, toggleButton, setActiveNavigation
 *   FormHandler  — generic form → API bridge
 *   OAuthHandler — Google/OAuth popup flow
 *   UserDataManager — load and render current user info
 *   App          — top-level orchestrator
 *
 * All of the above are also exposed on `window.*` for backward-compatible
 * inline scripts throughout the template tree.
 */

// ─── Constants ────────────────────────────────────────────────────────────────

const AppConfig = Object.freeze({
    MODAL_Z_INDEX:   1058,
    LOGIN_PATH:      '/signin',
    TOKEN_KEYS: {
        ACCESS:  'access_token',
        REFRESH: 'refresh_token',
    },
    HTTP: {
        OK:           200,
        UNAUTHORIZED: 401,
    },
});

// ─── Utils ────────────────────────────────────────────────────────────────────

const Utils = {
    getCookie(name) {
        try {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        } catch (_) {}
        return null;
    },

    /** Remove a cookie by name (works for non-HttpOnly cookies) */
    removeCookie(name, path = '/') {
        try {
            document.cookie = `${name}=; Max-Age=0; path=${path};`;
        } catch (_) {}
    },

    getStorage(key) {
        try { return localStorage.getItem(key); } catch (_) { return null; }
    },

    setStorage(key, value) {
        try {
            if (value && typeof value === 'string' && value.trim()) {
                localStorage.setItem(key, value.trim());
                return true;
            }
        } catch (_) {}
        return false;
    },

    removeStorage(key) {
        try { localStorage.removeItem(key); } catch (_) {}
    },

    getUrlParams() {
        try { return new URLSearchParams(window.location.search); }
        catch (_) { return new URLSearchParams(); }
    },

    cleanUrl() {
        try {
            window.history.replaceState(
                {}, document.title,
                window.location.href.split('?')[0].split('#')[0]
            );
        } catch (_) {}
    },

    isValidString(v) {
        return typeof v === 'string' && v.trim().length > 0;
    },

    /**
     * Strict JWT format validator.
     * A JWT must be three Base64url-encoded parts separated by dots.
     * Rejects "null", "undefined", "", "Bearer ", etc.
     */
    isValidJwt(token) {
        if (!this.isValidString(token)) return false;
        const parts = token.split('.');
        if (parts.length !== 3) return false;
        // Each part must be non-empty and contain only Base64url chars
        const b64urlRe = /^[A-Za-z0-9_-]+$/;
        return parts.every(p => p.length > 0 && b64urlRe.test(p));
    },

    /** Extract pathname from URL (handles absolute or relative) */
    getPathFromUrl(url) {
        try {
            return new URL(url).pathname;
        } catch (_) {
            return url; // relative
        }
    },

    /** Human-readable error from a failed fetch/API call */
    friendlyError(error) {
        console.error('Error:', error);
        if (!error) return 'An unexpected error occurred.';
        const msg = error.message || String(error);
        if (error.isNetworkError) return msg; // already worded by HttpClient
        if (/failed to fetch|networkerror|load failed|network request failed/i.test(msg)) {
            return NetworkMessage.build();
        }
        // Do NOT map 401/unauthorized generically — that masks real login errors.
        // The explicit "session expired" message is thrown by HttpClient only on
        // non-auth endpoints after a failed token refresh.
        return msg;
    },
};

// Network failures: say what is actually wrong (offline vs. server unreachable) and log the URL.
const NetworkMessage = {
    build() {
        if (typeof navigator !== 'undefined' && navigator.onLine === false) {
            return 'You appear to be offline. Please check your internet connection and try again.';
        }
        return 'We could not reach the server. Please try again in a moment.';
    },
};

// ─── ApiConfig ────────────────────────────────────────────────────────────────

/**
 * The API URL is decided ONCE on the server (see web.api_base_for_host) and injected by
 * templates/incs/metas.html as window.APP_CONFIG.API_BASE. Nothing else may guess it.
 */
const ApiConfig = {
    apiUrl:  null,
    planUrl: null,

    init() {
        const injected = (window.APP_CONFIG && window.APP_CONFIG.API_BASE) || window.apiUrl;
        if (!injected) console.error('APP_CONFIG.API_BASE is missing: check templates/incs/metas.html');
        this.apiUrl  = String(injected || `${window.location.origin}/api`).replace(/\/+$/, '');
        this.planUrl = `${this.apiUrl}/plans`;
        window.apiUrl  = this.apiUrl;   // global compat for page scripts
        window.planUrl = this.planUrl;
    },

    get() {
        return this.apiUrl || (this.init(), this.apiUrl);
    },
};

// ─── TokenManager ─────────────────────────────────────────────────────────────

const TokenManager = {
    getAccess() {
        return Utils.getStorage(AppConfig.TOKEN_KEYS.ACCESS)
            || Utils.getCookie(AppConfig.TOKEN_KEYS.ACCESS);
    },

    getRefresh() {
        return Utils.getStorage(AppConfig.TOKEN_KEYS.REFRESH);
    },

    setTokens(access, refresh) {
        if (Utils.isValidJwt(access))  Utils.setStorage(AppConfig.TOKEN_KEYS.ACCESS,  access);
        if (Utils.isValidJwt(refresh)) Utils.setStorage(AppConfig.TOKEN_KEYS.REFRESH, refresh);
    },

    clear() {
        Utils.removeStorage(AppConfig.TOKEN_KEYS.ACCESS);
        Utils.removeStorage(AppConfig.TOKEN_KEYS.REFRESH);
        // Also clear any cookie the backend may have set (best-effort)
        Utils.removeCookie(AppConfig.TOKEN_KEYS.ACCESS);
        Utils.removeCookie(AppConfig.TOKEN_KEYS.REFRESH);
    },

    /** Return true if either access or refresh token is present and looks valid */
    hasToken() {
        return Utils.isValidJwt(this.getAccess()) || Utils.isValidJwt(this.getRefresh());
    },

    /** Full logout: wipe storage + redirect to login (unless already there) */
    logout(redirectUrl = AppConfig.LOGIN_PATH) {
        this.clear();
        const current = window.location.pathname;
        if (!current.includes('signin') && !current.includes('login')) {
            window.location.href = redirectUrl;
        }
    },

    _inflight: null,

    /** One refresh at a time: parallel 401s share the same request. */
    refresh() {
        if (!this._inflight) {
            this._inflight = this._refresh().finally(() => { this._inflight = null; });
        }
        return this._inflight;
    },

    async _refresh() {
        const rt = this.getRefresh();
        if (!Utils.isValidJwt(rt)) return false;

        try {
            // Use raw fetch (not HttpClient) to avoid infinite recursion.
            // credentials: 'omit' prevents stale JWT cookies from triggering
            // CSRF errors on the refresh endpoint.
            // The refresh token travels in the Authorization header (the API only reads headers).
            const res = await fetch(`${ApiConfig.get()}/users/refresh-token`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${rt}` },
                credentials: 'omit',
            });
            if (!res.ok) return false;
            const data = await res.json();
            if (data.access_token)  Utils.setStorage(AppConfig.TOKEN_KEYS.ACCESS,  data.access_token);
            if (data.refresh_token) Utils.setStorage(AppConfig.TOKEN_KEYS.REFRESH, data.refresh_token);
            return true;
        } catch (_) {
            return false;
        }
    },
};

// ─── HttpClient ───────────────────────────────────────────────────────────────

const PUBLIC_ENDPOINT = /\/(signin|signup|refresh-token|reset-password|verify-email|resend-verification|authorize|callback|message)\b/;

const HttpClient = {
    async request(url, options = {}) {
        if (!url) throw new Error('URL is required');

        const path = Utils.getPathFromUrl(url);
        // Public endpoints never get an Authorization header (an expired token there would only cause a 401)
        const isAuthEndpoint = PUBLIC_ENDPOINT.test(path);

        // ── Auth header: only for non-auth endpoints AND only if JWT is well-formed ──
        const token   = isAuthEndpoint ? null : TokenManager.getAccess();
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (Utils.isValidJwt(token)) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // The API authenticates with bearer tokens only: no cookies, hence no CSRF headers either.
        const credentials = 'omit';

        const opts = {
            ...options,
            headers,
            mode: 'cors',
            credentials,
        };

        let res;
        try {
            res = await fetch(url, opts);
        } catch (networkErr) {
            throw networkErr.isNetworkError ? networkErr : Object.assign(new Error(NetworkMessage.build()), { isNetworkError: true });
        }

        // ── 401 handling ──
        if (res.status === AppConfig.HTTP.UNAUTHORIZED) {
            // Auth endpoints: do NOT attempt refresh — just surface the error
            if (isAuthEndpoint) {
                let errMsg = `Authentication failed (HTTP ${res.status})`;
                try {
                    const body = await res.json();
                    errMsg = body.error || body.message || errMsg;
                } catch (_) {}
                throw Object.assign(new Error(errMsg), { status: res.status });
            }

            // Non-auth endpoint: the fetch wrapper below already tried a silent refresh + retry.
            const hadTokenBefore = TokenManager.hasToken();
            // Session is dead. Clear everything and redirect.
            TokenManager.clear();
            if (hadTokenBefore) {
                // Only redirect if we actually had a session (avoid kicking
                // logged-out visitors on public pages to login).
                TokenManager.logout();
            }
            throw Object.assign(new Error('Your session has expired. Please sign in again.'), { status: 401 });
        }

        if (!res.ok) {
            let errMsg = `Request failed (HTTP ${res.status})`;
            try {
                const body = await res.json();
                errMsg = body.error || body.message || errMsg;
            } catch (_) {}
            throw Object.assign(new Error(errMsg), { status: res.status });
        }

        return res.json();
    },
};

// ─── API-aware fetch ──────────────────────────────────────────────────────────
// Every request to the API (from HttpClient AND from page scripts that call fetch directly):
//   • never sends cookies (bearer tokens only)
//   • on 401 for a protected endpoint: refreshes the access token once and retries
//   • turns browser network failures into one accurate, friendly message
(function installApiFetch() {
    const nativeFetch = window.fetch.bind(window);
    window.nativeFetch = nativeFetch;

    window.fetch = async function (input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        if (!url.startsWith(ApiConfig.get())) return nativeFetch(input, init);

        const opts = { ...(init || {}), credentials: 'omit' };
        let res;
        try {
            res = await nativeFetch(input, opts);
        } catch (networkErr) {
            console.error('Network error calling', url, '-', networkErr.message,
                          '(is the API up? ' + ApiConfig.get() + '/health)');
            throw Object.assign(new Error(NetworkMessage.build()), { isNetworkError: true });
        }

        const protectedCall = !PUBLIC_ENDPOINT.test(Utils.getPathFromUrl(url));
        if (res.status === AppConfig.HTTP.UNAUTHORIZED && protectedCall && Utils.isValidJwt(TokenManager.getRefresh())) {
            if (await TokenManager.refresh()) {
                const headers = new Headers(opts.headers || {});
                headers.set('Authorization', `Bearer ${TokenManager.getAccess()}`);
                return nativeFetch(input, { ...opts, headers });
            }
        }
        return res;
    };
})();

// ─── UIManager ────────────────────────────────────────────────────────────────

const UIManager = {
    showModal(message, type = 'warning') {
        try {
            const textEl  = document.getElementById('response_text');
            const modalEl = document.getElementById('response_modal');

            if (!textEl || !modalEl) { alert(message); return; }

            textEl.textContent = message;
            textEl.className   = `text-${type}`;
            modalEl.style.zIndex = AppConfig.MODAL_Z_INDEX;

            (new bootstrap.Modal(modalEl)).show();
        } catch (e) {
            console.error('UIManager.showModal failed:', e);
            alert(message);
        }
    },

    toggleButton(btn, disable = true) {
        if (!btn) return;
        btn.disabled = disable;
        if (disable) {
            if (!btn.dataset.originalHtml) btn.dataset.originalHtml = btn.innerHTML;
            btn.innerHTML =
                '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Loading…';
        } else {
            if (btn.dataset.originalHtml) {
                btn.innerHTML = btn.dataset.originalHtml;
                delete btn.dataset.originalHtml;
            }
        }
    },

    setActiveNavigation() {
        const page = window.location.pathname.split('/').pop() || '';
        document.querySelectorAll('nav a').forEach(link => {
            const href = (link.getAttribute('href') || '').split('/').pop();
            link.classList.toggle('active', href === page && page !== '');
        });
    },

    showToast(message, type = 'success') {
        const container = document.getElementById('toast-container')
                       || document.body;
        const id   = `toast-${Date.now()}`;
        const html = `
            <div id="${id}" class="toast align-items-center text-bg-${type} border-0 mb-2"
                 role="alert" aria-live="assertive" aria-atomic="true">
              <div class="d-flex">
                <div class="toast-body fw-medium">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto"
                        data-bs-dismiss="toast" aria-label="Close"></button>
              </div>
            </div>`;
        container.insertAdjacentHTML('beforeend', html);
        const el = document.getElementById(id);
        if (el && window.bootstrap && bootstrap.Toast) {
            const t = new bootstrap.Toast(el, { delay: 4000 });
            t.show();
            el.addEventListener('hidden.bs.toast', () => el.remove());
        }
    },
};

// ─── FormHandler ──────────────────────────────────────────────────────────────

const FormHandler = {
    init() {
        const configs = [
            { id: 'reset_password_modal', endpoint: 'users/reset-password' },
            { id: 'message_form',         endpoint: 'users/message'        },
            { id: 'add_plan_form',        endpoint: 'plans'                },
            { id: 'add_address_form',     endpoint: 'addresses'            },
            { id: 'service_form',         endpoint: 'services', onSuccess: FormHandler._onServiceSuccess },
        ];
        configs.forEach(cfg => this._attach(cfg.id, cfg.endpoint, cfg.onSuccess));
    },

    _attach(formId, endpoint, onSuccess) {
        const form = document.getElementById(formId);
        if (!form) return;
        form.addEventListener('submit', e => {
            e.preventDefault();
            this.submit(formId, endpoint, onSuccess);
        });
    },

    async submit(formId, endpoint, onSuccess) {
        const form   = document.getElementById(formId);
        if (!form) return;
        const btn    = form.querySelector('button[type="submit"]');
        const apiUrl = ApiConfig.get();

        try {
            UIManager.toggleButton(btn, true);

            const data = Object.fromEntries(new FormData(form).entries());

            // Detect auth endpoints by the endpoint path (consistent with HttpClient)
            const isAuthEndpoint = /(signin|signup)/.test(endpoint);

            // Scrub stale tokens before hitting auth endpoints so we don't send
            // a stale Bearer token that triggers a 401 before the route runs.
            if (isAuthEndpoint) {
                TokenManager.clear();
            }

            const result = await HttpClient.request(`${apiUrl}/${endpoint}`, {
                method: form.method?.toUpperCase() || 'POST',
                body: JSON.stringify(data),
            });

            if (result.success || result.id || result.message) {
                if (typeof onSuccess === 'function') {
                    onSuccess(result, form);
                } else {
                    UIManager.showModal(result.message || 'Done!', 'success');
                }

                // Handle signin-specific token storage
                if (endpoint === 'users/signin' && result.access_token) {
                    TokenManager.setTokens(result.access_token, result.refresh_token);
                    if (result.redirect) window.location.href = result.redirect;
                }
            } else {
                UIManager.showModal(result.error || 'Operation failed.', 'danger');
            }

        } catch (err) {
            UIManager.showModal(Utils.friendlyError(err), 'danger');
        } finally {
            UIManager.toggleButton(btn, false);
        }
    },

    _onServiceSuccess(result, form) {
        UIManager.showModal(
            result.message || 'Your service request has been received! We\'ll be in touch shortly.',
            'success'
        );
        form.reset();
        setTimeout(() => {
            const modalEl = form.closest('.modal');
            if (modalEl) {
                const bsModal = bootstrap.Modal.getInstance(modalEl);
                if (bsModal) bsModal.hide();
            }
        }, 2200);
    },
};

// ─── OAuthHandler ─────────────────────────────────────────────────────────────

const OAuthHandler = {
    init() {
        const btn = document.getElementById('google-signin-btn');
        if (btn) btn.addEventListener('click', () => this.initiate('google'));
        this._handleCallback();
    },

    async initiate(provider) {
        try {
            const res  = await fetch(`${ApiConfig.get()}/users/authorize/${provider}`, {
                headers: { 'Client-Callback-Url': window.location.origin + '/signin' },
                credentials: 'omit',
            });
            const data = await res.json().catch(() => ({}));
            if (res.ok && data.redirect) {
                window.location.href = data.redirect;
            } else {
                UIManager.showModal(data.error || 'Failed to initiate sign-in. Please try again.', 'danger');
            }
        } catch (err) {
            UIManager.showModal(Utils.friendlyError(err), 'danger');
        }
    },

    /** The API redirects back with the result in the URL fragment (never sent to servers or logs). */
    _handleCallback() {
        const raw = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : '';
        const params = new URLSearchParams(raw || window.location.search);
        const success = params.get('success');
        if (!success) return;

        if (success.toLowerCase() === 'true' && params.get('access_token')) {
            TokenManager.setTokens(params.get('access_token'), params.get('refresh_token'));
            Utils.cleanUrl();
            UIManager.showModal('Sign-in successful! Redirecting…', 'success');
            const redirect = params.get('redirect');
            setTimeout(() => { window.location.href = Utils.isValidString(redirect) && redirect.startsWith('/') ? redirect : '/account'; }, 1200);
        } else {
            Utils.cleanUrl();
            UIManager.showModal(params.get('error') || 'Sign-in failed. Please try again.', 'danger');
        }
    },
};

// ─── UserDataManager ──────────────────────────────────────────────────────────

const UserDataManager = {
    async load() {
        try {
            const data = await HttpClient.request(`${ApiConfig.get()}/users/current`);
            if (data) this._render(data);
        } catch (_) {
            // Non-fatal — user might simply not be logged in.
            // If they had a stale token, HttpClient already cleared it
            // and redirected; if they had no token, we silently ignore.
        }
    },

    _render(u) {
        const name    = u.name || u.username || '';
        const initial = name.charAt(0).toUpperCase();

        const setText = (sel, val) => {
            const el = document.querySelector(sel);
            if (el) el.textContent = val;
        };
        setText('.name',    name);
        setText('.initial', initial);

        const profileLink = document.querySelector('#profile_link, .btn.btn-dark.rounded-pill.animate-scale');
        if (profileLink) {
            profileLink.setAttribute('href', './settings');
            const span = profileLink.querySelector('span');
            if (span) span.textContent = u.username || name;
        }
    },
};

// ─── App ──────────────────────────────────────────────────────────────────────

const App = {
    async init() {
        try {
            UIManager.setActiveNavigation();
            FormHandler.init();
            OAuthHandler.init();

            const needsUser = document.querySelector('.name, .initial, #profile_link');
            if (needsUser) await UserDataManager.load();

        } catch (err) {
            console.error('App init error:', err);
        }
    },
};

// ─── Bootstrap ────────────────────────────────────────────────────────────────

ApiConfig.init();
window.make_request     = (url, opts)    => HttpClient.request(url, opts);
window.refresh_token    = ()             => TokenManager.refresh();
window.logout           = ()             => TokenManager.logout();
window.response_modal   = (msg, type)    => UIManager.showModal(msg, type);
window.toggleButton     = (btn, disable) => UIManager.toggleButton(btn, disable);
window.handleFormSubmit = (id, endpoint) => FormHandler.submit(id, endpoint);
window.Utils            = Utils;
window.TokenManager     = TokenManager;
window.get_user_home    = ()             => UserDataManager.load();
window.showToast        = (msg, type)    => UIManager.showToast(msg, type);
window.getToken         = ()             => TokenManager.getAccess();
window.getAuthHeaders   = ()             => (Utils.isValidJwt(TokenManager.getAccess()) ? { Authorization: `Bearer ${TokenManager.getAccess()}` } : {});

document.addEventListener('DOMContentLoaded', () => App.init());

