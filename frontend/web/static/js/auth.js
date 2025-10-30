// auth.js
// auth.js - Helper functions for authentication

// Function to validate the JWT token (now fetching from cookies)
function isValidToken(token) {
    if (!token) return false;

    const payload = JSON.parse(atob(token.split('.')[1])); // Decode the payload of the JWT
    const currentTime = Math.floor(Date.now() / 1000); // Current time in seconds

    return payload.exp > currentTime; // Check if token is not expired
}

window.isValidToken = isValidToken

// Function to get the token from cookies
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

window.getCookie = getCookie

// Function to check user roles from cookies/localStorage
function hasRequiredRoles(userRoles, requiredRoles) {
    return requiredRoles.every(role => userRoles.includes(role)); // Ensure user has all required roles
}

window.hasRequiredRoles = hasRequiredRoles

// Function to handle access control
function authRequired(requiredRoles = []) {
    const token = localStorage.getItem('access_token'); // Get the token from HTTP-only cookies
    const userRoles = window.getRolesFromDecodedToken(token); // Get user roles from token

    if (!token || !token.trim() || !isValidToken(token)) {
        window.response_modal("Access denied: User not authenticated or token invalid.");

        // Add a delay before redirecting
        setTimeout(function () {
            window.location.href = '/signin'; // Redirect to the login page if token is invalid
        }, 2000); // Delay of 2 seconds (2000 ms)

        return;
    }

    if (requiredRoles.length > 0 && !hasRequiredRoles(userRoles, requiredRoles)) {
        window.response_modal("Access denied: User does not have the required roles.");

        // Add a delay before redirecting
        setTimeout(function () {
            window.location.href = './account'; // Redirect to account page if the user doesn't have required roles
        }, 2000); // Delay of 2 seconds (2000 ms)

        return;
    }

    console.log("Access granted: User is authenticated and authorized.");
    // Continue with the page logic if authenticated and authorized
}


window.authRequired = authRequired

// Function to refresh the token if expired (using a refresh token)
async function refreshToken() {
    const refreshToken = getCookie('refresh_token'); // Retrieve refresh token from cookies
    if (!refreshToken) return;

    try {
        const response = await fetch(`${window.apiUrl}/users/refresh-token`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${refreshToken}` }
        });

        if (response.ok) {
            const data = await response.json();
            document.cookie = `access_token=${data.access_token}; path=/; HttpOnly`; // Set new access token
        } else {
            window.location.href = '/signin'; // Redirect to login if refresh fails
        }
    } catch (err) {
        window.response_modal("Error refreshing token", err);
        window.location.href = '/signin'; // Redirect to login on error
    }
}

window.refreshToken = refreshToken

// accessControl.js - Function to check route access control

// Example usage in a route (client-side page navigation check)
// const requiresAdminRole = true; // Determine if the current route requires the admin role

// // Check authentication and roles based on route requirements
// if (requiresAdminRole) {
//     authRequired(['admin']); // Check if the user has the 'admin' role
// } else {
//     console.log("Access granted to the page.");
//     // Continue with normal page logic
// }

// Function to decode JWT and extract roles
function getRolesFromDecodedToken(jwt) {
    // Check if the JWT is a valid string and not empty
    if (typeof jwt !== 'string' || !jwt.trim()) {
        console.error('Invalid JWT token');
        return []; // Return empty array if the JWT is invalid
    }

    // Split the JWT into its components
    const parts = jwt.split('.');

    // Check if the JWT has the correct number of parts (header, payload, signature)
    if (parts.length !== 3) {
        console.error('Invalid JWT format');
        return []; // Return empty array if the JWT format is incorrect
    }

    // Decode the payload using atob
    const decodedPayload = JSON.parse(atob(parts[1]));

    // Extract roles from the decoded payload
    const roles = decodedPayload.roles || []; // Default to empty array if roles are not present
    return roles;
}

window.getRolesFromDecodedToken = getRolesFromDecodedToken;

// Example JWT token (as provided)
// const jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc0MDYwMTI1NywianRpIjoiMzlhMDlmYmItZjg0Yy00OTk1LThhMmMtYjgwOTlmN2ViMDQyIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6ImphbWVzY2hyaXN0bzk2MkBnbWFpbC5jb20iLCJuYmYiOjE3NDA2MDEyNTcsImNzcmYiOiJlYmQ3ODA1Yi00NGEyLTQwNTgtODQ4My02YmYzZmI1MmZkM2UiLCJleHAiOjE3NDA2MDIxNTcsImlkIjoxLCJuYW1lIjoiTXIgUGF1bCIsInVzZXJuYW1lIjoicGF1bCIsImVtYWlsIjoiamFtZXNjaHJpc3RvOTYyQGdtYWlsLmNvbSIsInBob25lIjoiMDcwMjY1NjEzMjciLCJhYm91dF9tZSI6bnVsbCwiY3JlYXRlZF9hdCI6IlNhdCwgMDggRmViIDIwMjUgMTc6MzM6NDEgR01UIiwidXBkYXRlZF9hdCI6IlNhdCwgMDggRmViIDIwMjUgMTg6Mjc6MjYgR01UIiwicm9sZXMiOltdLCJ0b2tlbl90eXBlIjoiYWNjZXNzIn0.WXKdtgJy1Xx4yfMoUKcV0Mgzxz1BbBOajvY5fPu8D4M";

// Extract roles from the decoded JWT token
const userRoles = getRolesFromDecodedToken(localStorage.getItem('access_token'));
// console.log('User Roles:', userRoles); // Output: []

// Check if the user has the 'admin' role
if (!userRoles.includes('admin')) {
    // Disable the button and set the styles to show it is disabled
    const recordUsageBtn = document.getElementById('recordUsageBtn');

    if (recordUsageBtn) {
        // Update the background color of the span to pink and add !important to avoid CSS conflicts
        const spanElement = recordUsageBtn.querySelector('span');
        spanElement.style.backgroundColor = 'pink'; // Ensure this is the correct span
        spanElement.style.setProperty('background-color', 'pink', 'important'); // Use !important if needed

        // Add the disabled and grey background classes to the button
        recordUsageBtn.classList.add('disabled', 'text-bg-grey');

        // Set the button as disabled so it's not clickable
        recordUsageBtn.setAttribute('disabled', 'true');

        // Update the badge text to reflect no access
        recordUsageBtn.querySelector('.badge').innerText = "Only Admin can record usage when you submit fabrics.";
    }

    const admin_only = document.getElementById('admin-only');
    if(admin_only){
        admin_only.style.display = 'none';
        // alert(admin_only.style.display);
    }
}

// Check admin status and modify UI
function checkAdminStatus() {
  const token = localStorage.getItem('access_token');
  if (!token) return;
  
  const userRoles = window.getRolesFromDecodedToken(token);
  const isAdmin = userRoles.includes('admin');
  
  // Show/hide admin features
  document.querySelectorAll('.admin-only').forEach(el => {
    el.style.display = isAdmin ? '' : 'none';
  });
}

// Execute on page load
window.addEventListener('DOMContentLoaded', checkAdminStatus);