
// Application Configuration and Constants
const AppConfig = {
    PRODUCTION_DOMAIN: 'simplylovely.ng',
    PRODUCTION_API: 'https://api.simplylovely.ng/api',
    DEVELOPMENT_API: 'http://localhost:5001/api',
    MODAL_Z_INDEX: 1058,
    TOKEN_KEYS: {
        ACCESS: 'access_token',
        REFRESH: 'refresh_token'
    },
    HTTP_STATUS: {
        UNAUTHORIZED: 401,
        OK: 200
    }
};

// Utility Functions
const Utils = {
    /**
     * Safely get cookie value
     */
    getCookie(name) {
        try {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) {
                return parts.pop().split(';').shift();
            }
            return null;
        } catch (error) {
            console.warn(`Error getting cookie ${name}:`, error);
            return null;
        }
    },

    /**
     * Safely access localStorage
     */
    getStorageItem(key) {
        try {
            return localStorage.getItem(key);
        } catch (error) {
            console.warn(`Error accessing localStorage for key ${key}:`, error);
            return null;
        }
    },

    /**
     * Safely set localStorage
     */
    setStorageItem(key, value) {
        try {
            if (value && value.trim()) {
                localStorage.setItem(key, value.trim());
                return true;
            }
            return false;
        } catch (error) {
            console.warn(`Error setting localStorage for key ${key}:`, error);
            return false;
        }
    },

    /**
     * Get URL parameters safely
     */
    getUrlParams() {
        try {
            return new URLSearchParams(window.location.search);
        } catch (error) {
            console.warn('Error parsing URL parameters:', error);
            return new URLSearchParams();
        }
    },

    /**
     * Clean URL from query parameters
     */
    cleanUrl() {
        try {
            const url = window.location.href.split('?')[0];
            window.history.replaceState({}, document.title, url);
        } catch (error) {
            console.warn('Error cleaning URL:', error);
        }
    },

    /**
     * Validate required string
     */
    isValidString(str) {
        return str && typeof str === 'string' && str.trim().length > 0;
    }
};

// API Configuration Manager
const ApiConfig = {
    init() {
        this.apiUrl = this.determineApiUrl();
        this.planUrl = `${this.apiUrl}/plans`;
        
        // Expose to window for backward compatibility
        window.apiUrl = this.apiUrl;
        window.planUrl = this.planUrl;
        
        console.log('API Configuration initialized:', {
            environment: this.getEnvironment(),
            apiUrl: this.apiUrl
        });
    },

    determineApiUrl() {
        const hostname = window.location.hostname;
        return hostname === AppConfig.PRODUCTION_DOMAIN 
            ? AppConfig.PRODUCTION_API 
            : AppConfig.DEVELOPMENT_API;
    },

    getEnvironment() {
        return window.location.hostname === AppConfig.PRODUCTION_DOMAIN 
            ? 'production' 
            : 'development';
    }
};

// Token Management System
const TokenManager = {
    getAccessToken() {
        return Utils.getStorageItem(AppConfig.TOKEN_KEYS.ACCESS) || 
               Utils.getCookie(AppConfig.TOKEN_KEYS.ACCESS);
    },

    getRefreshToken() {
        return Utils.getStorageItem(AppConfig.TOKEN_KEYS.REFRESH);
    },

    setTokens(accessToken, refreshToken) {
        const results = {
            access: false,
            refresh: false
        };

        if (Utils.isValidString(accessToken)) {
            results.access = Utils.setStorageItem(AppConfig.TOKEN_KEYS.ACCESS, accessToken);
        } else {
            console.warn('Access token not provided or invalid');
        }

        if (Utils.isValidString(refreshToken)) {
            results.refresh = Utils.setStorageItem(AppConfig.TOKEN_KEYS.REFRESH, refreshToken);
        } else {
            console.warn('Refresh token not provided or invalid');
        }

        return results;
    },

    clearTokens() {
        try {
            localStorage.removeItem(AppConfig.TOKEN_KEYS.ACCESS);
            localStorage.removeItem(AppConfig.TOKEN_KEYS.REFRESH);
        } catch (error) {
            console.warn('Error clearing tokens:', error);
        }
    },

    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();
        
        if (!Utils.isValidString(refreshToken)) {
            console.warn('No valid refresh token available');
            return false;
        }

        try {
            console.log('Attempting token refresh...');
            
            const response = await fetch(`${ApiConfig.apiUrl}/users/refresh-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('Token refresh failed:', errorData);
                return false;
            }

            const data = await response.json();
            console.log('Token refresh successful');

            // Update tokens
            if (data.access_token) {
                Utils.setStorageItem(AppConfig.TOKEN_KEYS.ACCESS, data.access_token);
            }

            if (data.refresh_token) {
                Utils.setStorageItem(AppConfig.TOKEN_KEYS.REFRESH, data.refresh_token);
            }

            return true;
        } catch (error) {
            console.error('Error during token refresh:', error);
            return false;
        }
    }
};

// HTTP Request Handler
const HttpClient = {
    async makeRequest(url, options = {}) {
        if (!url) {
            throw new Error('URL is required for API request');
        }

        const token = TokenManager.getAccessToken();
        
        // Prepare headers
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        // Add authorization header if token exists
        if (Utils.isValidString(token)) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const requestOptions = {
            ...options,
            headers
        };

        try {
            console.log(`Making request to: ${url}`, {
                method: requestOptions.method || 'GET',
                hasAuth: !!headers['Authorization']
            });

            const response = await fetch(url, requestOptions);
            
            // Handle authentication errors
            if (response.status === AppConfig.HTTP_STATUS.UNAUTHORIZED) {
                console.log('Received 401, attempting token refresh...');
                
                const refreshed = await TokenManager.refreshAccessToken();
                if (refreshed) {
                    // Retry original request with new token
                    const newToken = TokenManager.getAccessToken();
                    if (newToken) {
                        requestOptions.headers['Authorization'] = `Bearer ${newToken}`;
                        return this.makeRequest(url, requestOptions);
                    }
                }
                
                throw new Error('Authentication failed. Please log in again.');
            }

            // Handle other HTTP errors
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage = errorData.error || `HTTP ${response.status}: ${response.statusText}`;
                throw new Error(errorMessage);
            }

            return await response.json();
        } catch (error) {
            console.error('Request failed:', {
                url,
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }
};

// UI Components Manager
const UIManager = {
    showModal(message) {
        try {
            const responseTextElement = document.getElementById('response_text');
            const modalElement = document.getElementById('response_modal');
            
            if (!responseTextElement || !modalElement) {
                console.warn('Modal elements not found, falling back to alert');
                alert(message);
                return;
            }

            responseTextElement.textContent = message;
            modalElement.style.zIndex = AppConfig.MODAL_Z_INDEX;
            
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        } catch (error) {
            console.error('Error showing modal:', error);
            alert(message); // Fallback
        }
    },

    toggleButton(button, disable = true, showSpinner = true) {
        if (!button) {
            console.warn('Button element not provided to toggleButton');
            return;
        }

        try {
            button.disabled = disable;
            
            if (showSpinner) {
                if (disable) {
                    // Save original text and show spinner
                    if (!button.dataset.originalText) {
                        button.dataset.originalText = button.innerHTML;
                    }
                    button.innerHTML = `
                        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                        Loading...
                    `;
                } else {
                    // Restore original text
                    const originalText = button.dataset.originalText;
                    if (originalText) {
                        button.innerHTML = originalText;
                        delete button.dataset.originalText;
                    }
                }
            }
        } catch (error) {
            console.error('Error toggling button:', error);
        }
    },

    setActiveNavigation() {
        try {
            const currentPage = window.location.pathname.split("/").pop();
            const navLinks = document.querySelectorAll("nav a");
            
            navLinks.forEach(link => {
                const href = link.getAttribute("href");
                if (href === currentPage) {
                    link.classList.add("active");
                } else {
                    link.classList.remove("active");
                }
            });
        } catch (error) {
            console.error('Error setting active navigation:', error);
        }
    }
};

// Form Handler
const FormHandler = {
    init() {
        this.attachFormListeners();
    },

    attachFormListeners() {
        const formConfigs = [
            { id: 'signup_form', action: 'users/signup' },
            { id: 'signin_form', action: 'users/signin' },
            { id: 'reset_password_modal', action: 'users/reset-password' },
            { id: 'message_form', action: 'users/send-message' },
            { id: 'add_plan_form', action: 'plans' },
            { id: 'add_address_form', action: 'addresses' }
        ];

        formConfigs.forEach(config => {
            const form = document.getElementById(config.id);
            if (form) {
                form.addEventListener('submit', (event) => {
                    event.preventDefault();
                    this.handleFormSubmit(config.id, config.action);
                });
            }
        });
    },

    async handleFormSubmit(formId, action) {
        const form = document.getElementById(formId);
        if (!form) {
            console.error(`Form with ID ${formId} not found`);
            return;
        }

        const submitButton = form.querySelector('button[type="submit"]');
        
        try {
            UIManager.toggleButton(submitButton, true, true);

            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            
            console.log(`Submitting form: ${formId}`, { action, dataKeys: Object.keys(data) });

            const result = await HttpClient.makeRequest(`${ApiConfig.apiUrl}/${action}`, {
                method: form.method || 'POST',
                body: JSON.stringify(data),
            });

            if (result.success) {
                await this.handleSuccessResponse(result, action);
            } else {
                UIManager.showModal(result.error || 'Operation failed.');
            }

        } catch (error) {
            console.error(`Form submission error for ${formId}:`, error);
            UIManager.showModal(`Error: ${error.message || 'Unexpected error occurred'}`);
        } finally {
            UIManager.toggleButton(submitButton, false, true);
        }
    },

    async handleSuccessResponse(result, action) {
        // Handle login-specific actions
        if (action === 'users/signin') {
            const tokenResults = TokenManager.setTokens(result.access_token, result.refresh_token);
            console.log('Tokens saved:', tokenResults);

            if (result.redirect) {
                window.location.href = result.redirect;
                return;
            }
        }

        UIManager.showModal(result.message || 'Operation successful.');
    }
};

// User Data Manager
const UserDataManager = {
    async loadUserData() {
        try {
            const data = await HttpClient.makeRequest(`${ApiConfig.apiUrl}/users/current`);
            this.updateUserDisplay(data);
        } catch (error) {
            console.error('Error loading user data:', error);
            // Don't show error modal for user data fetch failures
        }
    },

    updateUserDisplay(userData) {
        try {
            if (!userData || !userData.name) {
                console.warn('Invalid user data received');
                return;
            }

            // Update name display
            const nameElement = document.querySelector('.name');
            if (nameElement) {
                nameElement.textContent = userData.name;
            }

            // Update initial display
            const initialElement = document.querySelector('.initial');
            if (initialElement) {
                initialElement.textContent = userData.name.charAt(0).toUpperCase();
            }

            // Update account link
            const accountLink = document.querySelector('.btn.btn-dark.rounded-pill.animate-scale');
            if (accountLink && userData.username) {
                accountLink.setAttribute('href', './account');
                const span = accountLink.querySelector('span');
                if (span) {
                    span.textContent = userData.username;
                }
            }

            console.log('User display updated successfully');
        } catch (error) {
            console.error('Error updating user display:', error);
        }
    }
};

// OAuth Handler
const OAuthHandler = {
    init() {
        this.attachOAuthListeners();
        this.handleOAuthCallback();
    },

    attachOAuthListeners() {
        const googleSigninBtn = document.getElementById('google-signin-btn');
        if (googleSigninBtn) {
            googleSigninBtn.addEventListener('click', () => {
                this.initiateOAuth('google');
            });
        }
    },

    async initiateOAuth(provider) {
        try {
            console.log(`Initiating ${provider} OAuth...`);

            const response = await fetch(`${ApiConfig.apiUrl}/users/authorize/${provider}`, {
                method: 'GET',
                headers: {
                    'Client-Callback-Url': window.location.href,
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (response.ok && data.redirect) {
                window.location.href = data.redirect;
            } else {
                console.error('OAuth authorization error:', data);
                UIManager.showModal('Failed to initiate sign-in. Please try again.');
            }
        } catch (error) {
            console.error('OAuth error:', error);
            UIManager.showModal('An error occurred during sign-in. Please try again.');
        }
    },

    handleOAuthCallback() {
        const urlParams = Utils.getUrlParams();
        const success = urlParams.get('success');
        const accessToken = urlParams.get('access_token');
        const refreshToken = urlParams.get('refresh_token');

        if (!success && !accessToken && !refreshToken) {
            return; // No OAuth callback to handle
        }

        try {
            if (success === "True") {
                const tokenResults = TokenManager.setTokens(accessToken, refreshToken);
                console.log('OAuth tokens saved:', tokenResults);

                UIManager.showModal("Sign-in successful!");

                const redirectUrl = urlParams.get("redirect");
                if (Utils.isValidString(redirectUrl)) {
                    setTimeout(() => {
                        window.location.href = redirectUrl.trim();
                    }, 1500);
                }
            } else {
                UIManager.showModal(`Sign-in failed: ${success}. Please try again.`);
            }

            // Clean URL after handling callback
            Utils.cleanUrl();
        } catch (error) {
            console.error('Error handling OAuth callback:', error);
            UIManager.showModal('Error processing sign-in. Please try again.');
        }
    }
};

// Main Application Controller
const App = {
    async init() {
        try {
            console.log('Initializing application...');

            // Initialize core components
            ApiConfig.init();
            
            // Expose global functions for backward compatibility
            this.exposeGlobalFunctions();
            
            // Initialize UI components
            UIManager.setActiveNavigation();
            FormHandler.init();
            OAuthHandler.init();

            // Load user data if user elements exist
            if (this.shouldLoadUserData()) {
                await UserDataManager.loadUserData();
            }

            console.log('Application initialized successfully');
        } catch (error) {
            console.error('Application initialization failed:', error);
        }
    },

    exposeGlobalFunctions() {
        // Expose functions to window for backward compatibility
        window.make_request = HttpClient.makeRequest.bind(HttpClient);
        window.refresh_token = TokenManager.refreshAccessToken.bind(TokenManager);
        window.response_modal = UIManager.showModal.bind(UIManager);
        window.toggleButton = UIManager.toggleButton.bind(UIManager);
        window.handleFormSubmit = FormHandler.handleFormSubmit.bind(FormHandler);
    },

    shouldLoadUserData() {
        return document.querySelector('.name') || 
               document.querySelector('.initial') || 
               document.querySelector('.btn.btn-dark.rounded-pill.animate-scale span');
    }
};

// Initialize application when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    App.init();
});

// Initialize authentication check when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    if (typeof window.authRequired === 'function') {
        window.authRequired();
    } else {
        console.warn('window.authRequired function not found');
    }
});