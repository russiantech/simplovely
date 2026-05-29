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
        return JSON.parse(atob(parts[1]));
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

/**
 * Guard a page by auth/role requirements.
 * Redirects to /signin if unauthenticated; to /account if missing roles.
 */
function authRequired(requiredRoles = []) {
    const token = localStorage.getItem('access_token');

    if (!token || !isValidToken(token)) {
        if (window.response_modal) {
            window.response_modal('Access denied: please sign in to continue.');
        }
        setTimeout(() => { window.location.href = '/signin'; }, 1800);
        return false;
    }

    if (requiredRoles.length > 0) {
        const userRoles = getRolesFromDecodedToken(token);
        if (!hasRequiredRoles(userRoles, requiredRoles)) {
            if (window.response_modal) {
                window.response_modal('Access denied: you do not have the required permissions.');
            }
            setTimeout(() => { window.location.href = '/account'; }, 1800);
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
    const isAdmin = roles.includes('admin');

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
window.getRolesFromDecodedToken = getRolesFromDecodedToken;
window.decodeJwtPayload         = decodeJwtPayload;

// ─── DOM-ready work ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', applyAdminVisibility);
