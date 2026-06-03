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
    PROD_HOSTNAME:   'simplylovely.ng',
    PROD_API:        'https://api.simplylovely.ng/api',
    DEV_API:         'http://localhost:5001/api',
    MODAL_Z_INDEX:   1058,
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
                window.location.href.split('?')[0]
            );
        } catch (_) {}
    },

    isValidString(v) {
        return typeof v === 'string' && v.trim().length > 0;
    },

    /** Human-readable error from a failed fetch/API call */
    friendlyError(error) {
        console.error('Error:', error);
        if (!error) return 'An unexpected error occurred.';
        const msg = error.message || String(error);
        if (msg === 'Failed to fetch' || msg.includes('NetworkError') || msg.includes('network')) {
            return 'Unable to connect to the server. Please check your internet connection and try again.';
        }
        if (msg.includes('401') || msg.toLowerCase().includes('unauthorized')) {
            return 'Your session has expired. Please sign in again.';
        }
        return msg;
    },
};

// ─── ApiConfig ────────────────────────────────────────────────────────────────

const ApiConfig = {
    apiUrl:  null,
    planUrl: null,

    init() {
        this.apiUrl  = this._resolveUrl();
        this.planUrl = `${this.apiUrl}/plans`;

        // Global compat
        window.apiUrl  = this.apiUrl;
        window.planUrl = this.planUrl;
    },

    _resolveUrl() {
        const h = window.location.hostname;
        if (h === AppConfig.PROD_HOSTNAME || h.endsWith('.' + AppConfig.PROD_HOSTNAME)) {
            return AppConfig.PROD_API;
        }
        return AppConfig.DEV_API;
    },

    get() {
        return this.apiUrl || this._resolveUrl();
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
        if (Utils.isValidString(access))  Utils.setStorage(AppConfig.TOKEN_KEYS.ACCESS,  access);
        if (Utils.isValidString(refresh)) Utils.setStorage(AppConfig.TOKEN_KEYS.REFRESH, refresh);
    },

    clear() {
        Utils.removeStorage(AppConfig.TOKEN_KEYS.ACCESS);
        Utils.removeStorage(AppConfig.TOKEN_KEYS.REFRESH);
    },

    async refresh() {
        const rt = this.getRefresh();
        if (!Utils.isValidString(rt)) return false;

        try {
            const res = await fetch(`${ApiConfig.get()}/users/refresh-token`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ refresh_token: rt }),
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

const HttpClient = {
    async request(url, options = {}) {
        if (!url) throw new Error('URL is required');

        const token   = TokenManager.getAccess();
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (Utils.isValidString(token)) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // const opts = { ...options, headers };
        const opts = { 
            ...options, 
            headers,
            mode: 'cors',           // ← ADD THIS
            credentials: 'include',  // ← ADD THIS if using cookies
        };

        let res;
        try {
            res = await fetch(url, opts);
        } catch (networkErr) {
            // Wrap the raw browser network error with a friendly message
            const friendly = Utils.friendlyError(networkErr);
            const err = new Error(friendly);
            err.isNetworkError = true;
            console.error('Network error:', url, networkErr.message);
            throw err;
        }

        // Auto-refresh on 401
        if (res.status === AppConfig.HTTP.UNAUTHORIZED) {
            console.log(res)
            const refreshed = await TokenManager.refresh();
            if (refreshed) {
                const newToken = TokenManager.getAccess();
                if (newToken) opts.headers['Authorization'] = `Bearer ${newToken}`;
                return this.request(url, opts);
            }
            throw new Error('Your session has expired. Please sign in again.');
        }

        if (!res.ok) {
            let errMsg = `Request failed (HTTP ${res.status})`;
            try {
                const body = await res.json();
                errMsg = body.error || body.message || errMsg;
            } catch (_) {}
            throw new Error(errMsg);
        }

        return res.json();
    },
};

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
        // Lightweight inline toast fallback; upgrades gracefully when toast container exists
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
            { id: 'message_form',         endpoint: 'users/send-message'   },
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

            const data   = Object.fromEntries(new FormData(form).entries());

            // 
            const isAuthEndpoint = endpoint.includes('signin') || endpoint.includes('signup');

            // Temporarily clear tokens for auth endpoints so we don't send stale auth
            if (isAuthEndpoint) {
                TokenManager.clear();
            }

            const result = await HttpClient.request(`${apiUrl}/${endpoint}`, {
                method: form.method?.toUpperCase() || 'POST',
                body: JSON.stringify(data),
            });

            // If this was an auth endpoint but we got no token, restore previous tokens (if any)
            // if (isAuthEndpoint && !result.access_token) {
            //     const prevAccess  = TokenManager.getAccess();
            //     const prevRefresh = TokenManager.getRefresh();
            //     if (prevAccess)  Utils.setStorage(AppConfig.TOKEN_KEYS.ACCESS,  prevAccess);
            //     if (prevRefresh) Utils.setStorage(AppConfig.TOKEN_KEYS.REFRESH, prevRefresh);
            // }

            // const result = await HttpClient.request(`${apiUrl}/${endpoint}`, {
            //     method: form.method?.toUpperCase() || 'POST',
            //     body:   JSON.stringify(data),
            // });

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
        // Close the modal after a brief delay
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
                headers: {
                    'Client-Callback-Url': window.location.href,
                    'Content-Type':        'application/json',
                },
            });
            const data = await res.json();
            if (res.ok && data.redirect) {
                window.location.href = data.redirect;
            } else {
                UIManager.showModal('Failed to initiate sign-in. Please try again.', 'danger');
            }
        } catch (err) {
            UIManager.showModal(Utils.friendlyError(err), 'danger');
        }
    },

    _handleCallback() {
        const params = Utils.getUrlParams();
        const success = params.get('success');
        const access  = params.get('access_token');
        const refresh = params.get('refresh_token');

        if (!success && !access) return;

        if (success === 'True') {
            TokenManager.setTokens(access, refresh);
            UIManager.showModal('Sign-in successful! Redirecting…', 'success');
            const redirect = params.get('redirect');
            if (Utils.isValidString(redirect)) {
                setTimeout(() => { window.location.href = redirect.trim(); }, 1500);
            }
        } else {
            UIManager.showModal('Sign-in failed. Please try again.', 'danger');
        }
        Utils.cleanUrl();
    },
};

// ─── UserDataManager ──────────────────────────────────────────────────────────

const UserDataManager = {
    async load() {
        try {
            const data = await HttpClient.request(`${ApiConfig.get()}/users/current`);
            if (data) this._render(data);
        } catch (_) {
            // Non-fatal — user might simply not be logged in
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
            ApiConfig.init();
            this._exposeGlobals();
            UIManager.setActiveNavigation();
            FormHandler.init();
            OAuthHandler.init();

            const needsUser = document.querySelector('.name, .initial, #profile_link');
            if (needsUser) await UserDataManager.load();

        } catch (err) {
            console.error('App init error:', err);
        }
    },

    _exposeGlobals() {
        // Backward-compat window.* bindings
        window.make_request     = (url, opts)    => HttpClient.request(url, opts);
        window.refresh_token    = ()             => TokenManager.refresh();
        window.response_modal   = (msg, type)    => UIManager.showModal(msg, type);
        window.toggleButton     = (btn, disable) => UIManager.toggleButton(btn, disable);
        window.handleFormSubmit = (id, endpoint) => FormHandler.submit(id, endpoint);
        window.Utils            = Utils;
        window.TokenManager     = TokenManager;
        window.get_user_home    = ()             => UserDataManager.load();
    },
};

// ─── Bootstrap ────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => App.init());
