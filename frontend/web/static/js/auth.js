// VERSION 01
// auth.js
// // auth.js - Helper functions for authentication

// // Function to validate the JWT token (now fetching from cookies)
// function isValidToken(token) {
//     if (!token) return false;

//     const payload = JSON.parse(atob(token.split('.')[1])); // Decode the payload of the JWT
//     const currentTime = Math.floor(Date.now() / 1000); // Current time in seconds

//     return payload.exp > currentTime; // Check if token is not expired
// }

// window.isValidToken = isValidToken

// // Function to get the token from cookies
// function getCookie(name) {
//     const value = `; ${document.cookie}`;
//     const parts = value.split(`; ${name}=`);
//     if (parts.length === 2) return parts.pop().split(';').shift();
//     return null;
// }

// window.getCookie = getCookie

// // Function to check user roles from cookies/localStorage
// function hasRequiredRoles(userRoles, s) {
//     return requiredRoles.every(role => userRoles.includes(role)); // Ensure user has all required roles
// }

// window.hasRequiredRoles = hasRequiredRoles

// // Function to handle access control
// function authRequired(requiredRoles = []) {
//     const token = localStorage.getItem('access_token'); // Get the token from HTTP-only cookies
//     const userRoles = window.getRolesFromDecodedToken(token); // Get user roles from token

//     if (!token || !token.trim() || !isValidToken(token)) {
//         window.response_modal("Access denied: User not authenticated or token invalid.");

//         // Add a delay before redirecting
//         setTimeout(function () {
//             window.location.href = '/signin'; // Redirect to the login page if token is invalid
//         }, 2000); // Delay of 2 seconds (2000 ms)

//         return;
//     }

//     if (requiredRoles.length > 0 && !hasRequiredRoles(userRoles, requiredRoles)) {
//         window.response_modal("Access denied: User does not have the required roles.");

//         // Add a delay before redirecting
//         setTimeout(function () {
//             window.location.href = './account'; // Redirect to account page if the user doesn't have required roles
//         }, 2000); // Delay of 2 seconds (2000 ms)

//         return;
//     }

//     console.log("Access granted: User is authenticated and authorized.");
//     // Continue with the page logic if authenticated and authorized
// }


// window.authRequired = authRequired

// // Function to refresh the token if expired (using a refresh token)
// async function refreshToken() {
//     const refreshToken = getCookie('refresh_token'); // Retrieve refresh token from cookies
//     if (!refreshToken) return;

//     try {
//         const response = await fetch(`${window.apiUrl}/users/refresh-token`, {
//             method: 'POST',
//             headers: { 'Authorization': `Bearer ${refreshToken}` }
//         });

//         if (response.ok) {
//             const data = await response.json();
//             document.cookie = `access_token=${data.access_token}; path=/; HttpOnly`; // Set new access token
//         } else {
//             window.location.href = '/signin'; // Redirect to login if refresh fails
//         }
//     } catch (err) {
//         window.response_modal("Error refreshing token", err);
//         window.location.href = '/signin'; // Redirect to login on error
//     }
// }

// window.refreshToken = refreshToken

// // accessControl.js - Function to check route access control

// // Example usage in a route (client-side page navigation check)
// // const requiresAdminRole = true; // Determine if the current route requires the admin role

// // // Check authentication and roles based on route requirements
// // if (requiresAdminRole) {
// //     authRequired(['admin']); // Check if the user has the 'admin' role
// // } else {
// //     console.log("Access granted to the page.");
// //     // Continue with normal page logic
// // }

// // Function to decode JWT and extract roles
// function getRolesFromDecodedToken(jwt) {
//     // Check if the JWT is a valid string and not empty
//     if (typeof jwt !== 'string' || !jwt.trim()) {
//         console.error('Invalid JWT token');
//         return []; // Return empty array if the JWT is invalid
//     }

//     // Split the JWT into its components
//     const parts = jwt.split('.');

//     // Check if the JWT has the correct number of parts (header, payload, signature)
//     if (parts.length !== 3) {
//         console.error('Invalid JWT format');
//         return []; // Return empty array if the JWT format is incorrect
//     }

//     // Decode the payload using atob
//     const decodedPayload = JSON.parse(atob(parts[1]));

//     // Extract roles from the decoded payload
//     const roles = decodedPayload.roles || []; // Default to empty array if roles are not present
//     return roles;
// }

// window.getRolesFromDecodedToken = getRolesFromDecodedToken;

// // Example JWT token (as provided)
// // const jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc0MDYwMTI1NywianRpIjoiMzlhMDlmYmItZjg0Yy00OTk1LThhMmMtYjgwOTlmN2ViMDQyIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6ImphbWVzY2hyaXN0bzk2MkBnbWFpbC5jb20iLCJuYmYiOjE3NDA2MDEyNTcsImNzcmYiOiJlYmQ3ODA1Yi00NGEyLTQwNTgtODQ4My02YmYzZmI1MmZkM2UiLCJleHAiOjE3NDA2MDIxNTcsImlkIjoxLCJuYW1lIjoiTXIgUGF1bCIsInVzZXJuYW1lIjoicGF1bCIsImVtYWlsIjoiamFtZXNjaHJpc3RvOTYyQGdtYWlsLmNvbSIsInBob25lIjoiMDcwMjY1NjEzMjciLCJhYm91dF9tZSI6bnVsbCwiY3JlYXRlZF9hdCI6IlNhdCwgMDggRmViIDIwMjUgMTc6MzM6NDEgR01UIiwidXBkYXRlZF9hdCI6IlNhdCwgMDggRmViIDIwMjUgMTg6Mjc6MjYgR01UIiwicm9sZXMiOltdLCJ0b2tlbl90eXBlIjoiYWNjZXNzIn0.WXKdtgJy1Xx4yfMoUKcV0Mgzxz1BbBOajvY5fPu8D4M";

// // Extract roles from the decoded JWT token
// const userRoles = getRolesFromDecodedToken(localStorage.getItem('access_token'));
// // console.log('User Roles:', userRoles); // Output: []

// // Check if the user has the 'admin' role
// if (!userRoles.includes('admin')) {
//     // Disable the button and set the styles to show it is disabled
//     const recordUsageBtn = document.getElementById('recordUsageBtn');

//     if (recordUsageBtn) {
//         // Update the background color of the span to pink and add !important to avoid CSS conflicts
//         const spanElement = recordUsageBtn.querySelector('span');
//         spanElement.style.backgroundColor = 'pink'; // Ensure this is the correct span
//         spanElement.style.setProperty('background-color', 'pink', 'important'); // Use !important if needed

//         // Add the disabled and grey background classes to the button
//         recordUsageBtn.classList.add('disabled', 'text-bg-grey');

//         // Set the button as disabled so it's not clickable
//         recordUsageBtn.setAttribute('disabled', 'true');

//         // Update the badge text to reflect no access
//         recordUsageBtn.querySelector('.badge').innerText = "Only Admin can record usage when you submit fabrics.";
//     }

//     const createPlanBtn = document.getElementById('createPlanBtn');
//     if (createPlanBtn) {
  
//         // opens the usage modal instead
//         createPlanBtn.setAttribute('href', '#modalFullscreenUsage');

//         // Update the badge text to reflect no access
//         createPlanBtn.querySelector('.badge').innerText = "See Usage.";
//     }
// }


// VERSION 02

// // auth.js - Authentication Utilities

// /**
//  * Authentication Service Module
//  * Provides functions for token validation, role checking, and authentication state management
//  */
// const AuthService = (function() {
//     // Private constants
//     const TOKEN_KEY = 'access_token';
//     const REFRESH_TOKEN_KEY = 'refresh_token';
//     const LOGIN_REDIRECT_DELAY = 2000; // 2 seconds

//     /**
//      * Decodes a JWT token payload
//      * @param {string} token - JWT token
//      * @returns {object|null} Decoded payload or null if invalid
//      */
//     function decodeTokenPayload(token) {
//         if (!token) return null;
        
//         try {
//             const payloadBase64 = token.split('.')[1];
//             if (!payloadBase64) return null;
            
//             const payloadJson = atob(payloadBase64);
//             return JSON.parse(payloadJson);
//         } catch (error) {
//             console.error('Token decoding failed:', error);
//             return null;
//         }
//     }

//     /**
//      * Checks if a token is valid (exists and not expired)
//      * @param {string} token - JWT token to validate
//      * @returns {boolean} True if valid, false otherwise
//      */
//     function isValidToken(token) {
//         if (!token) return false;
        
//         const payload = decodeTokenPayload(token);
//         if (!payload || !payload.exp) return false;
        
//         const currentTime = Math.floor(Date.now() / 1000);
//         return payload.exp > currentTime;
//     }

//     /**
//      * Gets a cookie value by name
//      * @param {string} name - Cookie name
//      * @returns {string|null} Cookie value or null if not found
//      */
//     function getCookie(name) {
//         const value = `; ${document.cookie}`;
//         const parts = value.split(`; ${name}=`);
//         if (parts.length === 2) return parts.pop().split(';').shift();
//         return null;
//     }

//     /**
//      * Checks if user has all required roles
//      * @param {array} userRoles - User's roles
//      * @param {array} requiredRoles - Roles to check against
//      * @returns {boolean} True if user has all required roles
//      */
//     function hasRequiredRoles(userRoles = [], requiredRoles = []) {
//         if (!Array.isArray(userRoles) || !Array.isArray(requiredRoles)) return false;
//         return requiredRoles.every(role => userRoles.includes(role));
//     }

//     /**
//      * Extracts roles from a JWT token
//      * @param {string} jwt - JWT token
//      * @returns {array} Array of roles or empty array if none
//      */
//     function getRolesFromToken(jwt) {
//         const payload = decodeTokenPayload(jwt);
//         return payload?.roles || [];
//     }

//     /**
//      * Checks if user is authenticated (has valid token)
//      * @returns {boolean} True if authenticated
//      */
//     function isAuthenticated() {
//         const token = localStorage.getItem(TOKEN_KEY);
//         return isValidToken(token);
//     }

//     /**
//      * Redirects to account page if already authenticated
//      * Useful for login/register pages to prevent duplicate auth
//      */
//     function redirectIfAuthenticated() {
//         if (isAuthenticated()) {
//             setTimeout(() => {
//                 window.location.href = '/account';
//             }, LOGIN_REDIRECT_DELAY);
//         }
//     }

//     /**
//      * Enforces authentication and role requirements
//      * @param {array} requiredRoles - Required roles for access
//      */
//     function enforceAuth(requiredRoles = []) {
//         const token = localStorage.getItem(TOKEN_KEY);
//         const userRoles = getRolesFromToken(token);

//         if (!isValidToken(token)) {
//             window.response_modal("Access denied: User not authenticated or token invalid.");
//             setTimeout(() => {
//                 window.location.href = '/signin';
//             }, LOGIN_REDIRECT_DELAY);
//             return;
//         }

//         if (requiredRoles.length > 0 && !hasRequiredRoles(userRoles, requiredRoles)) {
//             window.response_modal("Access denied: User does not have the required roles.");
//             setTimeout(() => {
//                 window.location.href = '/account';
//             }, LOGIN_REDIRECT_DELAY);
//             return;
//         }
//     }

//     /**
//      * Attempts to refresh the access token using refresh token
//      * @returns {Promise<void>}
//      */
//     async function refreshToken() {
//         const refreshToken = getCookie(REFRESH_TOKEN_KEY);
//         if (!refreshToken) {
//             window.location.href = '/signin';
//             return;
//         }

//         try {
//             const response = await fetch(`${window.apiUrl}/users/refresh-token`, {
//                 method: 'POST',
//                 headers: { 'Authorization': `Bearer ${refreshToken}` }
//             });

//             if (!response.ok) throw new Error('Refresh failed');

//             const data = await response.json();
//             localStorage.setItem(TOKEN_KEY, data.access_token);
//         } catch (err) {
//             window.response_modal("Error refreshing token", err);
//             window.location.href = '/signin';
//         }
//     }

//     /**
//      * Applies role-based UI restrictions
//      */
//     function applyRoleRestrictions() {
//         if (!isAuthenticated()) return;
        
//         const token = localStorage.getItem(TOKEN_KEY);
//         const userRoles = getRolesFromToken(token);

//         if (!userRoles.includes('admin')) {
//             // Disable record usage button for non-admins
//             const recordUsageBtn = document.getElementById('recordUsageBtn');
//             if (recordUsageBtn) {
//                 const spanElement = recordUsageBtn.querySelector('span');
//                 if (spanElement) {
//                     spanElement.style.backgroundColor = 'pink';
//                     spanElement.style.setProperty('background-color', 'pink', 'important');
//                 }
                
//                 recordUsageBtn.classList.add('disabled', 'text-bg-grey');
//                 recordUsageBtn.disabled = true;
                
//                 const badge = recordUsageBtn.querySelector('.badge');
//                 if (badge) {
//                     badge.innerText = "Only Admin can record usage when you submit fabrics.";
//                 }
//             }

//             // Modify create plan button for non-admins
//             const createPlanBtn = document.getElementById('createPlanBtn');
//             if (createPlanBtn) {
//                 createPlanBtn.setAttribute('href', '#modalFullscreenUsage');
                
//                 const badge = createPlanBtn.querySelector('.badge');
//                 if (badge) {
//                     badge.innerText = "See Usage.";
//                 }
//             }
//         }
//     }

//     // Public API
//     return {
//         isValidToken,
//         getCookie,
//         hasRequiredRoles,
//         getRolesFromToken,
//         isAuthenticated,
//         redirectIfAuthenticated,
//         enforceAuth,
//         refreshToken,
//         applyRoleRestrictions
//     };
// })();

// // Attach to window if needed (better to use module imports in modern JS)
// window.AuthService = AuthService;

// // Initialize role restrictions when DOM is loaded
// document.addEventListener('DOMContentLoaded', AuthService.applyRoleRestrictions);


// VERSION 03
// auth.js - Window-bound Authentication Utilities

/**
 * Authentication Utilities
 * Provides window-bound functions for authentication and authorization
 */

// Constants
const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const LOGIN_REDIRECT_DELAY = 2000; // 2 seconds

// ======================
// Core Utility Functions
// ======================

/**
 * Decodes JWT token payload safely
 * @param {string} token - JWT token
 * @returns {object|null} Decoded payload or null
 */
function _decodeTokenPayload(token) {
    if (!token) return null;
    
    try {
        const payloadBase64 = token.split('.')[1];
        return payloadBase64 ? JSON.parse(atob(payloadBase64)) : null;
    } catch (error) {
        console.error('Token decoding failed:', error);
        return null;
    }
}

// ======================
// Public API Functions
// ======================

/**
 * Checks if token exists and is not expired
 * @param {string} token - JWT token
 * @returns {boolean} Validity status
 */
window.isValidToken = function(token) {
    if (!token) return false;
    
    const payload = _decodeTokenPayload(token);
    return payload?.exp > Math.floor(Date.now() / 1000);
};

/**
 * Gets cookie value by name
 * @param {string} name - Cookie name
 * @returns {string|null} Cookie value
 */
window.getCookie = function(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    return parts.length === 2 ? parts.pop().split(';').shift() : null;
};

/**
 * Checks if user has all required roles
 * @param {array} userRoles - User's roles
 * @param {array} requiredRoles - Required roles
 * @returns {boolean} Authorization status
 */
window.hasRequiredRoles = function(userRoles = [], requiredRoles = []) {
    return Array.isArray(userRoles) && 
           Array.isArray(requiredRoles) &&
           requiredRoles.every(role => userRoles.includes(role));
};

/**
 * Extracts roles from JWT token
 * @param {string} jwt - JWT token
 * @returns {array} User roles
 */
window.getRolesFromToken = function(jwt) {
    const payload = _decodeTokenPayload(jwt);
    return payload?.roles || [];
};
// 
// Extract roles from the decoded JWT token
const userRoles = getRolesFromToken(localStorage.getItem('access_token'));
console.log('User Roles:', userRoles); // Output: []

/**
 * Checks if user is authenticated
 * @returns {boolean} Authentication status
 */
window.isAuthenticated = function() {
    const token = localStorage.getItem(TOKEN_KEY);
    return window.isValidToken(token);
};

/**
 * Redirects authenticated users away from auth pages
 */
window.redirectIfAuthenticated = function() {
    if (window.isAuthenticated()) {
        setTimeout(() => {
            window.location.href = '/account';
        }, LOGIN_REDIRECT_DELAY);
    }
};

/**
 * Enforces authentication and authorization
 * @param {array} requiredRoles - Required roles
 */
window.enforceAuth = function(requiredRoles = []) {
    const token = localStorage.getItem(TOKEN_KEY);
    const userRoles = window.getRolesFromToken(token);

    if (!window.isValidToken(token)) {
        window.response_modal("Access denied: Invalid or expired token");
        setTimeout(() => window.location.href = '/signin', LOGIN_REDIRECT_DELAY);
        return;
    }

    if (requiredRoles.length && !window.hasRequiredRoles(userRoles, requiredRoles)) {
        window.response_modal("Access denied: Insufficient privileges");
        setTimeout(() => window.location.href = '/account', LOGIN_REDIRECT_DELAY);
    }
};

/**
 * Attempts to refresh access token
 * @returns {Promise<void>}
 */
window.refreshToken = async function() {
    const refreshToken = window.getCookie(REFRESH_TOKEN_KEY);
    if (!refreshToken) {
        window.location.href = '/signin';
        return;
    }

    try {
        const response = await fetch(`${window.apiUrl}/users/refresh-token`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${refreshToken}` }
        });

        if (!response.ok) throw new Error('Refresh failed');
        
        const data = await response.json();
        localStorage.setItem(TOKEN_KEY, data.access_token);
    } catch (err) {
        console.error('Token refresh failed:', err);
        window.location.href = '/signin';
    }
};

/**
 * Applies UI restrictions based on user roles
 */
// window.applyAuthRestrictions = function() {
//     if (!window.isAuthenticated()) return;
    
//     const token = localStorage.getItem(TOKEN_KEY);
//     const userRoles = window.getRolesFromToken(token);

//     if (!userRoles.includes('admin')) {
//         // Admin-restricted elements
//         const adminElements = [
//             { id: 'recordUsageBtn', badgeText: "Only Admin can record usage when you submit fabrics." },
//             { id: 'createPlanBtn', badgeText: "See Usage.", action: btn => btn.setAttribute('href', '#modalFullscreenUsage') }
//         ];

//         adminElements.forEach(({ id, badgeText, action }) => {
//             const element = document.getElementById(id);
//             if (!element) return;

//             if (action) action(element);
            
//             const badge = element.querySelector('.badge');
//             if (badge) badge.innerText = badgeText;

//             element.classList.add('disabled', 'text-bg-grey');
//             element.disabled = true;
//         });
//     }
// };
// 
/**
 * Applies UI restrictions based on user roles
 */
window.applyAuthRestrictions = function() {
    if (!window.isAuthenticated()) return;
    
    const token = localStorage.getItem(TOKEN_KEY);
    const userRoles = window.getRolesFromToken(token);

    if (!userRoles.includes('admin')) {
        // Disable record usage button completely for non-admins
        const recordUsageBtn = document.getElementById('recordUsageBtn');
        if (recordUsageBtn) {
            const spanElement = recordUsageBtn.querySelector('span');
            if (spanElement) {
                spanElement.style.backgroundColor = 'pink';
                spanElement.style.setProperty('background-color', 'pink', 'important');
            }
            
            recordUsageBtn.classList.add('disabled', 'text-bg-grey');
            recordUsageBtn.disabled = true;
            
            const badge = recordUsageBtn.querySelector('.badge');
            if (badge) {
                badge.innerText = "Only Admin can record usage when you submit fabrics.";
            }
        }

        // Modify create plan button to show usage instead (without disabling)
        const createPlanBtn = document.getElementById('createPlanBtn');
        if (createPlanBtn) {
            createPlanBtn.setAttribute('href', '#modalFullscreenUsage');
            
            const badge = createPlanBtn.querySelector('.badge');
            if (badge) {
                badge.innerText = "See Usage.";
            }
            
            // Remove any disabled states if they exist
            createPlanBtn.classList.remove('disabled', 'text-bg-grey');
            createPlanBtn.disabled = false;
        }
    }
};

// Initialize restrictions when DOM loads
document.addEventListener('DOMContentLoaded', window.applyAuthRestrictions);

// Authentication check
document.addEventListener('DOMContentLoaded', function () {

    if (typeof window.authRequired === 'function') {
        window.authRequired();

    } else {
        console.warn('window.authRequired function not found');
    }
    
});