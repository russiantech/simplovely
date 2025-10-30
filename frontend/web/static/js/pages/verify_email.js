// /static/js/pages/verify_email.js

document.addEventListener('DOMContentLoaded', () => {
    const CONFIG = {
        REDIRECT_DELAY: 3000, // 3 seconds
        SELECTORS: {
            loading: 'verification-loading',
            success: 'verification-success',
            already: 'verification-already',
            error: 'verification-error',
            resendForm: 'resend-form',
            resendBtn: 'resend-verification',
            resendFormElement: 'resend-verification-form',
            resendEmail: 'resend-email',
            cancelResend: 'cancel-resend',
            errorMessage: 'error-message'
        }
    };

    // Utility functions
    const Utils = {
        getElement(id) {
            const element = document.getElementById(id);
            if (!element) {
                console.warn(`Element with ID '${id}' not found`);
            }
            return element;
        },

        showState(stateId) {
            // Hide all states
            Object.values(CONFIG.SELECTORS).forEach(selector => {
                const element = this.getElement(selector);
                if (element && element.classList.contains('verification-state')) {
                    element.classList.add('d-none');
                }
            });

            // Show requested state
            const stateElement = this.getElement(stateId);
            if (stateElement) {
                stateElement.classList.remove('d-none');
            }
        },

        getQueryParams() {
            const params = new URLSearchParams(window.location.search);
            return {
                token: params.get('token')
            };
        },

        removeQueryParameters() {
            const url = window.location.href.split('?')[0];
            window.history.replaceState({}, document.title, url);
        },

        setButtonLoading(button, isLoading) {
            if (!button) return;

            if (isLoading) {
                button.disabled = true;
                button.dataset.originalText = button.innerHTML;
                button.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Processing...
                `;
            } else {
                button.disabled = false;
                button.innerHTML = button.dataset.originalText || button.innerHTML;
            }
        }
    };

    // Email Verification Handler
    const VerificationHandler = {
        async verifyEmail(token) {
            if (!token) {
                console.error('No verification token provided');
                this.showError('Invalid verification link. No token provided.');
                return;
            }

            try {
                Utils.showState(CONFIG.SELECTORS.loading);

                const response = await fetch(`${window.apiUrl}/users/verify-email/${token}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                const data = await response.json();

                if (data.success) {
                    if (data.data && data.data.already_verified) {
                        this.showAlreadyVerified();
                    } else {
                        this.showSuccess(data.message);
                    }
                } else {
                    this.showError(data.error || 'Verification failed. Please try again.');
                }

            } catch (error) {
                console.error('Verification error:', error);
                this.showError('Unable to verify email. Please check your connection and try again.');
            }
        },

        showSuccess(message) {
            Utils.showState(CONFIG.SELECTORS.success);
            
            // Optional: Auto-redirect after delay
            setTimeout(() => {
                window.location.href = './signin';
            }, CONFIG.REDIRECT_DELAY);
        },

        showAlreadyVerified() {
            Utils.showState(CONFIG.SELECTORS.already);
            
            // Optional: Auto-redirect after delay
            setTimeout(() => {
                window.location.href = './signin';
            }, CONFIG.REDIRECT_DELAY);
        },

        showError(message) {
            Utils.showState(CONFIG.SELECTORS.error);
            
            const errorMessageElement = Utils.getElement(CONFIG.SELECTORS.errorMessage);
            if (errorMessageElement) {
                errorMessageElement.textContent = message;
            }
        },

        async resendVerification(email) {
            if (!email || !this.validateEmail(email)) {
                if (window.response_modal) {
                    window.response_modal('Please enter a valid email address.');
                }
                return false;
            }

            try {
                const response = await fetch(`${window.apiUrl}/users/resend-verification`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email: email })
                });

                const data = await response.json();

                if (data.success) {
                    if (window.response_modal) {
                        window.response_modal('Verification email sent! Please check your inbox.');
                    }
                    
                    // Hide resend form
                    const resendFormElement = Utils.getElement(CONFIG.SELECTORS.resendForm);
                    if (resendFormElement) {
                        resendFormElement.classList.add('d-none');
                    }
                    
                    return true;
                } else {
                    if (window.response_modal) {
                        window.response_modal(data.error || 'Failed to send verification email.');
                    }
                    return false;
                }

            } catch (error) {
                console.error('Resend verification error:', error);
                if (window.response_modal) {
                    window.response_modal('Unable to send verification email. Please try again.');
                }
                return false;
            }
        },

        validateEmail(email) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(String(email).toLowerCase());
        }
    };

    // Event Handlers
    const EventHandlers = {
        init() {
            // Resend verification button
            const resendBtn = Utils.getElement(CONFIG.SELECTORS.resendBtn);
            if (resendBtn) {
                resendBtn.addEventListener('click', () => {
                    const resendFormElement = Utils.getElement(CONFIG.SELECTORS.resendForm);
                    if (resendFormElement) {
                        resendFormElement.classList.remove('d-none');
                    }
                });
            }

            // Cancel resend button
            const cancelResendBtn = Utils.getElement(CONFIG.SELECTORS.cancelResend);
            if (cancelResendBtn) {
                cancelResendBtn.addEventListener('click', () => {
                    const resendFormElement = Utils.getElement(CONFIG.SELECTORS.resendForm);
                    if (resendFormElement) {
                        resendFormElement.classList.add('d-none');
                    }
                });
            }

            // Resend form submission
            const resendForm = Utils.getElement(CONFIG.SELECTORS.resendFormElement);
            if (resendForm) {
                resendForm.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const emailInput = Utils.getElement(CONFIG.SELECTORS.resendEmail);
                    const submitBtn = resendForm.querySelector('button[type="submit"]');
                    
                    if (!emailInput) return;

                    const email = emailInput.value.trim();
                    
                    Utils.setButtonLoading(submitBtn, true);
                    
                    await VerificationHandler.resendVerification(email);
                    
                    Utils.setButtonLoading(submitBtn, false);
                    
                    // Clear form
                    emailInput.value = '';
                });
            }
        }
    };

    // Application Initialization
    const App = {
        async init() {
            try {
                // Check if API URL is configured
                if (!window.apiUrl) {
                    throw new Error('API URL not configured');
                }

                // Initialize event handlers
                EventHandlers.init();

                // Get verification token from URL
                const { token } = Utils.getQueryParams();

                if (token) {
                    // Verify the token
                    await VerificationHandler.verifyEmail(token);
                    
                    // Remove token from URL for security
                    Utils.removeQueryParameters();
                } else {
                    // No token provided
                    VerificationHandler.showError('No verification token provided. Please check your email for the verification link.');
                }

            } catch (error) {
                console.error('Application initialization error:', error);
                VerificationHandler.showError('An error occurred during initialization. Please try again.');
            }
        }
    };

    // Start the application
    App.init();
});