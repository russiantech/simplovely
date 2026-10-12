// auth.js — Authentication helpers
// All functions are guard-safe and DRY.
// No immediate DOM-mutating code at parse time — all DOM work runs in DOMContentLoaded.

// ─── JWT helpers ──────────────────────────────────────────────────────────────

/**
 * Decode JWT payload safely. Returns null on any failure.
 */
function decodeJwtPayload(token) {
    try {
        if (typeof token !== 'string' || !token.trim()) return null;
        const parts = token.split('.');
        if (parts.length !== 3) return null;
        // JWTs are base64url (-, _, no padding) and UTF-8: plain atob() fails on many valid tokens.
        const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(parts[1].length / 4) * 4, '=');
        const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
        return JSON.parse(new TextDecoder().decode(bytes));
    } catch (_) {
        return null;
    }
}

/**
 * Returns true if the token exists and is not expired.
 */
function isValidToken(token) {
    const payload = decodeJwtPayload(token);
    if (!payload) return false;
    const now = Math.floor(Date.now() / 1000);
    return payload.exp > now;
}

/**
 * Extract roles array from a JWT. Returns [] on any failure.
 */
function getRolesFromDecodedToken(token) {
    const payload = decodeJwtPayload(token);
    if (!payload) return [];
    return Array.isArray(payload.roles) ? payload.roles : [];
}

// ─── Cookie helper ────────────────────────────────────────────────────────────

function getCookie(name) {
    try {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    } catch (_) {}
    return null;
}

// ─── Role checks ──────────────────────────────────────────────────────────────

function hasRequiredRoles(userRoles, requiredRoles) {
    return requiredRoles.every(role => userRoles.includes(role));
}

const ADMIN_ROLES = ['admin', 'dev'];

function isAdminToken(token) {
    return getRolesFromDecodedToken(token).some(r => ADMIN_ROLES.includes(r));
}

/**
 * Guard a page by auth/role requirements. Returns a Promise<boolean>.
 * An expired access token is silently renewed with the refresh token before giving up.
 * Redirects to /signin if unauthenticated; to /account if the roles are missing
 * (admins/devs always satisfy any role requirement).
 */
async function authRequired(requiredRoles = []) {
    let token = localStorage.getItem('access_token');

    if ((!token || !isValidToken(token)) && window.TokenManager) {
        if (await window.TokenManager.refresh()) token = localStorage.getItem('access_token');
    }

    if (!token || !isValidToken(token)) {
        if (window.response_modal) window.response_modal('Please sign in to continue.');
        setTimeout(() => { window.location.href = '/signin'; }, 1500);
        return false;
    }

    if (requiredRoles.length > 0 && !isAdminToken(token)) {
        if (!hasRequiredRoles(getRolesFromDecodedToken(token), requiredRoles)) {
            if (window.response_modal) window.response_modal('Access denied: you do not have the required permissions.');
            setTimeout(() => { window.location.href = '/account'; }, 1500);
            return false;
        }
    }
    return true;
}

// ─── Admin UI ─────────────────────────────────────────────────────────────────

/**
 * Show/hide elements based on whether the current user is an admin.
 * Called on DOMContentLoaded — safe to use querySelector.
 */
function applyAdminVisibility() {
    const token = localStorage.getItem('access_token');
    const roles = getRolesFromDecodedToken(token);
    const isAdmin = roles.some(r => ADMIN_ROLES.includes(r));

    // Toggle .admin-only elements
    document.querySelectorAll('.admin-only').forEach(el => {
        el.style.display = isAdmin ? '' : 'none';
    });

    // Disable the "record usage" button for non-admins
    if (!isAdmin) {
        const btn = document.getElementById('recordUsageBtn');
        if (btn) {
            btn.classList.add('disabled');
            btn.setAttribute('disabled', 'true');

            const badge = btn.querySelector('.badge');
            if (badge) {
                badge.innerText = 'Only admins can record usage after submitting fabrics.';
            }

            const span = btn.querySelector('span:not(.badge)');
            if (span) {
                span.style.setProperty('background-color', 'pink', 'important');
            }
        }

        const adminOnlyEl = document.getElementById('admin-only');
        if (adminOnlyEl) adminOnlyEl.style.display = 'none';
    }
}

// ─── Expose to window ─────────────────────────────────────────────────────────

window.isValidToken             = isValidToken;
window.getCookie                = getCookie;
window.hasRequiredRoles         = hasRequiredRoles;
window.authRequired             = authRequired;
window.isAdminToken             = isAdminToken;
window.getRolesFromDecodedToken = getRolesFromDecodedToken;
window.decodeJwtPayload         = decodeJwtPayload;

// ─── DOM-ready work ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', applyAdminVisibility);
