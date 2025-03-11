        // Function to validate the JWT token
        function isValidToken(token) {
            if (!token) return false;
            
            const payload = JSON.parse(atob(token.split('.')[1])); // Decode the payload of the JWT
            const currentTime = Math.floor(Date.now() / 1000); // Current time in seconds

            return payload.exp > currentTime; // Check if token is not expired
        }

        // Function to check user roles
        function hasRequiredRoles(userRoles, requiredRoles) {
            return requiredRoles.every(role => userRoles.includes(role)); // Ensure user has all required roles
        }

        // Function to handle access control
        function authRequired(requiredRoles = []) {
            const token = localStorage.getItem('access_token'); // Get the token from localStorage
            const userRoles = JSON.parse(localStorage.getItem('user_roles')) || []; // Get user roles from localStorage
            
            if (!token || !isValidToken(token)) {
                //console.error("Access denied: User not authenticated or token invalid.");
                window.response_modal("Access denied: User not authenticated or token invalid.");
                window.location.href = '/signin'; // Redirect to the login page if token is invalid
                return;
            }

            if (requiredRoles.length > 0 && !hasRequiredRoles(userRoles, requiredRoles)) {
                window.response_modal("Access denied: User does not have the required roles.");
                // console.error("Access denied: User does not have the required roles.");
                window.location.href = '/account'; // Redirect to the login page if the user doesn't have required roles
                return;
            }

            console.log("Access granted: User is authenticated and authorized.");
            // Continue with the page logic if authenticated and authorized
        }

        // Example usage in a route
        const requiresAdminRole = true; // Determine if the current route requires admin role

        // Check authentication and roles based on route requirements
        if (requiresAdminRole) {
            authRequired(['admin']); // Check if the user has the 'admin' role
        } else {
            console.log("Access granted to the page.");
            // Continue with normal page logic
        }