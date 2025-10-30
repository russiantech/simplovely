// V3

// /js/pages/account.js
document.addEventListener("DOMContentLoaded", () => {
    // Configuration and constants
    const CONFIG = {
        LOW_UNITS_THRESHOLD: 20,
        CURRENCY_OPTIONS: {
            style: 'currency',
            currency: 'NGN',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        },
        SELECTORS: {
            unitsUsed: 'units-used',
            usageProgress: 'usage-progress',
            unitsLeft: 'units-left',
            plansContainer: '.plans-container'
        }
    };

    // Utility functions
    const Utils = {
        /**
         * Safely get DOM element by ID with error handling
         */
        getElement(id) {
            const element = document.getElementById(id);
            if (!element) {
                console.warn(`Element with ID '${id}' not found`);
            }
            return element;
        },

        /**
         * Safely query selector with error handling
         */
        querySelector(selector) {
            const element = document.querySelector(selector);
            if (!element) {
                console.warn(`Element with selector '${selector}' not found`);
            }
            return element;
        },

        /**
         * Safely access nested object properties
         */
        safeGet(obj, path, defaultValue = null) {
            try {
                return path.split('.').reduce((current, key) => current?.[key], obj) ?? defaultValue;
            } catch (error) {
                console.warn(`Error accessing property '${path}':`, error);
                return defaultValue;
            }
        },

        /**
         * Format currency with error handling
         */
        formatCurrency(amount) {
            try {
                if (typeof amount !== 'number' || isNaN(amount)) {
                    console.warn('Invalid amount for currency formatting:', amount);
                    return 'N/A';
                }
                return amount.toLocaleString('en-NG', CONFIG.CURRENCY_OPTIONS);
            } catch (error) {
                console.error('Error formatting currency:', error);
                return `₦${amount.toFixed(2)}`;
            }
        },

        /**
         * Validate email address
         */
        validateEmail(email) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(String(email).toLowerCase());
        },

        /**
         * Show loading spinner in container
         */
        showLoadingSpinner(container) {
            if (!container) return;
            container.innerHTML = `
                <div class="d-flex justify-content-center align-items-center p-4">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
        },

        /**
         * Clear container content
         */
        clearContainer(container) {
            if (container) {
                container.innerHTML = '';
            }
        }
    };

    // Usage Statistics Handler
    const UsageStatistics = {
        async fetch() {
            try {
                // Check if required functions exist
                if (!window.make_request) {
                    throw new Error('window.make_request function not available');
                }
                if (!window.apiUrl) {
                    throw new Error('window.apiUrl not defined');
                }

                console.log('Fetching usage statistics from:', `${window.apiUrl}/usage/statistics`);
                
                // Add timeout and retry logic
                const data = await this.makeRequestWithRetry(`${window.apiUrl}/usage/statistics`);
                // console.log('Usage statistics data received:', data);

                if (!data) {
                    // console.warn('No data received from server, using default values');
                    this.updateDisplay(this.getDefaultData());
                    return;
                }

                this.updateDisplay(data);
            } catch (error) {
                console.error('Error fetching usage statistics:', error);

                // Try to display default data instead of showing error
                this.updateDisplay(this.getDefaultData());
                this.handleError(error);
            }
        },

        async makeRequestWithRetry(url, maxRetries = 2, delay = 1000) {
            for (let attempt = 1; attempt <= maxRetries; attempt++) {
                try {
                    // console.log(`Usage stats request attempt ${attempt}/${maxRetries}`);
                    
                    // Try with a simpler request first
                    const data = await window.make_request(url);
                    return data;
                } catch (error) {
                   // console.warn(`Attempt ${attempt} failed:`, error.message);
                    
                    if (attempt === maxRetries) {
                        throw error;
                    }
                    
                    // Wait before retry
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        },

        getDefaultData() {
            return {
                units_used: 0,
                total_units: 0,
                remaining_units: 0,
                usage_percentage: 0
            };
        },

        updateDisplay(data) {
            try {
                // Safely extract data with defaults
                const unitsUsed = Utils.safeGet(data, 'units_used', 0);
                const totalUnits = Utils.safeGet(data, 'total_units', 0);
                const remainingUnits = Utils.safeGet(data, 'remaining_units', 0);
                const usagePercentage = Utils.safeGet(data, 'usage_percentage', 0);

                // Update units used display
                const unitsUsedElement = Utils.getElement(CONFIG.SELECTORS.unitsUsed);
                if (unitsUsedElement) {
                    unitsUsedElement.textContent = `${unitsUsed} units used of ${totalUnits}`;
                }

                // Update progress bar
                this.updateProgressBar(usagePercentage);

                // Update remaining units
                this.updateRemainingUnits(remainingUnits);

            } catch (error) {
                console.error('Error updating usage display:', error);
            }
        },

        updateProgressBar(usagePercentage) {
            const usageProgressElement = Utils.getElement(CONFIG.SELECTORS.usageProgress);
            if (!usageProgressElement) return;

            try {
                const percentage = Math.round((usagePercentage || 0) * 100) / 100;
                const clampedPercentage = Math.max(0, Math.min(100, percentage));

                usageProgressElement.style.width = `${clampedPercentage}%`;
                usageProgressElement.textContent = `${clampedPercentage}%`;
                usageProgressElement.setAttribute('aria-valuenow', clampedPercentage);
            } catch (error) {
                console.error('Error updating progress bar:', error);
            }
        },

        updateRemainingUnits(remainingUnits) {
            const unitsLeftElement = Utils.getElement(CONFIG.SELECTORS.unitsLeft);
            if (!unitsLeftElement) return;

            try {
                const units = remainingUnits || 0;
                unitsLeftElement.textContent = `Remaining ${units} units`;

                // Handle low units warning
                if (units <= CONFIG.LOW_UNITS_THRESHOLD) {
                    unitsLeftElement.classList.add('text-danger');
                    
                    // Check if warning already exists to avoid duplicates
                    if (!unitsLeftElement.querySelector('.low-units-warning')) {
                        const warningSpan = document.createElement('span');
                        warningSpan.className = 'low-units-warning';
                        warningSpan.textContent = ' (Low units Alert. Please Recharge!)';
                        unitsLeftElement.appendChild(warningSpan);
                    }
                } else {
                    unitsLeftElement.classList.remove('text-danger');
                    const warningElement = unitsLeftElement.querySelector('.low-units-warning');
                    if (warningElement) {
                        warningElement.remove();
                    }
                }
            } catch (error) {
                console.error('Error updating remaining units:', error);
            }
        },

        handleError(error) {
            const errorMessage = `Error fetching usage statistics: ${error.message || 'Unknown error'}`;
            if (window.response_modal) {
                console.error(errorMessage);
                // window.response_modal(errorMessage);
            } else {
                console.error(errorMessage);
                // alert(errorMessage); // Fallback
            }
        }
    };

    // Plans Management
    const PlansManager = {
        init() {
            this.container = Utils.querySelector(CONFIG.SELECTORS.plansContainer);
            if (!this.container) {
                console.warn("Plans container not found. Plans functionality disabled.");
                return;
            }
            this.fetchPlans();
        },

        async fetchPlans() {
            try {
                if (!window.apiUrl) {
                    throw new Error('API URL not available');
                }

                Utils.showLoadingSpinner(this.container);
                // console.log('Fetching plans from:', `${window.apiUrl}/plans`);

                // Use fetch instead of make_request for plans to avoid the same error
                const response = await fetch(`${window.apiUrl}/plans`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                // console.log('Plans data received:', data);
                
                Utils.clearContainer(this.container);

                if (!data || !data.success) {
                    console.warn('Plans request unsuccessful:', data);
                    this.container.innerHTML = '<tr><td colspan="4" class="text-center py-4">Unable to load plans at this time</td></tr>';
                    return;
                }

                if (!Array.isArray(data.plans) || data.plans.length === 0) {
                    console.warn('No plans available in response');
                    this.container.innerHTML = '<tr><td colspan="4" class="text-center py-4">No plans available</td></tr>';
                    return;
                }

                this.renderPlans(data.plans);
                this.attachEventListeners();

            } catch (error) {
                console.error('Error fetching plans:', error);
                Utils.clearContainer(this.container);
                
                // Show a more user-friendly message
                this.container.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center py-4">
                            <div class="text-muted">
                                <p>Unable to load plans at this time.</p>
                                <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
                                    Try Again
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }
        },

        renderPlans(plans) {
            if (!Array.isArray(plans) || plans.length === 0) {
                this.container.innerHTML = '<tr><td colspan="4" class="text-center py-4">No plans available</td></tr>';
                return;
            }

            plans.forEach((plan, index) => {
                try {
                    const planRow = this.createPlanRow(plan, index);
                    this.container.insertAdjacentHTML('beforeend', planRow);
                } catch (error) {
                    console.error(`Error rendering plan at index ${index}:`, error, plan);
                }
            });
        },

        createPlanRow(plan, index) {
            // Safely extract plan data with defaults
            const planId = Utils.safeGet(plan, 'id', `plan-${index}`);
            const planName = Utils.safeGet(plan, 'name', 'Unnamed Plan');
            const planAmount = Utils.safeGet(plan, 'amount', 0);
            const planUnits = Utils.safeGet(plan, 'units', 'N/A');

            return `
                <tr class="cursor-pointer">
                    <td class="py-3 ps-0">
                        <div class="d-flex align-items-start align-items-md-center">
                            <div class="ratio bg-body-secondary rounded-2 overflow-hidden flex-shrink-0" style="width: 66px">
                                <img src="static/img/account/products/03.jpg" 
                                     class="hover-effect-target" 
                                     alt="Plan image"
                                     onerror="this.style.display='none'">
                            </div>
                            <div class="ps-2 ms-1">
                                <h6 class="product mb-1 mb-md-0">
                                    <span class="fs-sm fw-medium">${this.escapeHtml(planName)}</span>
                                </h6>
                            </div>
                        </div>
                    </td>
                    <td class="d-none d-md-table-cell py-3">
                        <span class="badge fs-xs text-info bg-info-subtle rounded-pill">
                            ${Utils.formatCurrency(planAmount)}
                        </span>
                    </td>
                    <td class="text-end d-none d-sm-table-cell py-3">${this.escapeHtml(planUnits)}</td>
                    <td class="text-end py-3">
                        <button class="btn btn-sm btn-dark rounded-pill subscribe-btn" 
                                data-plan-id="${this.escapeHtml(planId)}"
                                type="button">
                            Recharge
                        </button>
                    </td>
                </tr>
            `;
        },

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        attachEventListeners() {
            if (!this.container) return;

            this.container.addEventListener('click', (event) => {
                if (event.target.classList.contains('subscribe-btn')) {
                    event.preventDefault();
                    const button = event.target;
                    const planId = button.dataset.planId;
                    
                    if (planId) {
                        PaymentHandler.subscribe(planId, null, button);
                    } else {
                        console.error('Plan ID not found for button');
                    }
                }
            });
        },

        handleError(message) {
            if (window.response_modal) {
                window.response_modal(message);
            } else {
                console.error(message);
                // alert(message);
            }
        }
    };

    // Payment Handler
    const PaymentHandler = {
        async subscribe(planId, email, button) {
            if (!planId) {
                console.error('Plan ID is required for subscription');
                return;
            }

            try {
                this.setButtonLoading(button, true);
                console.log('Initiating payment for plan:', planId);

                // Check if make_request is available, fallback to fetch
                let response;
                const requestBody = { email: email };
                
                if (window.make_request && typeof window.make_request === 'function') {
                    try {
                        response = await window.make_request(`${window.apiUrl}/payment/${planId}/paystack`, {
                            method: "POST",
                            headers: {
                                'Content-Type': 'application/json',
                                'Client-Callback-Url': window.location.href,
                            },
                            body: JSON.stringify(requestBody),
                        });
                        // console.log(`response from plan payments: ${response}`);

                    } catch (makeRequestError) {
                        console.warn('make_request failed, falling back to fetch:', makeRequestError);
                        // Fallback to regular fetch
                        const fetchResponse = await fetch(`${window.apiUrl}/payment/${planId}/paystack`, {
                            method: "POST",
                            headers: {
                                'Content-Type': 'application/json',
                                'Client-Callback-Url': window.location.href,
                            },
                            body: JSON.stringify(requestBody),
                        });
                        
                        if (!fetchResponse.ok) {
                            // window.response_modal(JSON.stringify(makeRequestError) || "Error processing payment");
                            // throw new Error(`HTTP error! status: ${fetchResponse.status}`);
                            console.error(`Error processing payment. HTTP error! status: ${fetchResponse.status}`);
                            throw new Error(`Could not process payment at the moment, pls try again/inform admin about this.`);
                        }
                        response = await fetchResponse.json();
                    }
                } else {
                    // Use fetch directly if make_request is not available
                    const fetchResponse = await fetch(`${window.apiUrl}/payment/${planId}/paystack`, {
                        method: "POST",
                        headers: {
                            'Content-Type': 'application/json',
                            'Client-Callback-Url': window.location.href,
                        },
                        body: JSON.stringify(requestBody),
                    });
                    
                    if (!fetchResponse.ok) {
                        throw new Error(`HTTP error! status: ${fetchResponse.status}`);
                    }
                    response = await fetchResponse.json();
                }

                this.setButtonLoading(button, false);

                if (response && response.success && response.redirect) {
                    console.log('Payment initiated successfully, redirecting...');
                    window.location.href = response.redirect;
                } else {
                    const errorMessage = Utils.safeGet(response.error, 'error', 'Error processing payment');
                    console.error('Payment error:', errorMessage);
                    this.handleError(errorMessage);
                }

            } catch (error) {
                console.error('Subscription error:', error);
                this.setButtonLoading(button, false);
                this.handleError(`Error: ${error.message || 'Unknown error occurred'}`);
            }

            // 
        //     if (response.success) {
        //     window.location.href = response.redirect;
        // } else {
        //     button.innerHTML = 'Subscribe'; // Reset button text
        //     window.response_modal(response.error || "Error processing payment");
        // }
        // 
        },

        setButtonLoading(button, isLoading) {
            if (!button) return;

            if (isLoading) {
                button.disabled = true;
                button.innerHTML = `
                    <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    Loading...
                `;
            } else {
                button.disabled = false;
                button.innerHTML = 'Recharge';
            }
        },

        handleError(message) {
            if (window.response_modal) {
                window.response_modal(message);
            } else {
                console.error(message);
                // alert(message);
            }
        }
    };

    // URL Parameter Handler
    const URLHandler = {
        getQueryParams() {
            try {
                const params = new URLSearchParams(window.location.search);
                return {
                    status: params.get('status'),
                    reference: params.get('reference') || params.get('trxref')
                };
            } catch (error) {
                console.error('Error parsing URL parameters:', error);
                return {};
            }
        },

        removeQueryParameters() {
            try {
                const url = window.location.href;
                const baseUrl = url.split('?')[0];
                window.history.replaceState({}, document.title, baseUrl);
            } catch (error) {
                console.error('Error removing query parameters:', error);
            }
        },

        async handlePaymentCallback() {
            const queryParams = this.getQueryParams();
            
            if (!queryParams.reference) {
                return; // No payment callback to handle
            }

            try {
                if (window.response_modal) {
                    window.response_modal('Verifying your transaction, please wait...');
                }

                const response = await fetch(`${window.apiUrl}/payment/callback/paystack?reference=${queryParams.reference}`);
                
                // if (!response.ok) {
                //     // throw new Error(`HTTP error! status: ${response.status}`);
                //     throw new Error(`HTTP error! status: ${response.status}`);
                // }

                const result = await response.json();
                console.log('Payment verification result:', result);

                const message = result.success 
                    ? (result.message || "Transaction completed successfully!")
                    : (result.error || "Error processing transaction.");

                if (window.response_modal) {
                    window.response_modal(message);
                }

                this.removeQueryParameters();

            } catch (error) {
                console.error('Payment callback error:', error);
                const errorMessage = `Error: ${error.error || error.error || "Unknown error occurred."}`;
                if (window.response_modal) {
                    window.response_modal(errorMessage);
                }
            }
        }
    };

    // Application Initialization
    const App = {
        async init() {
            try {
                // Ensure required global functions exist
                if (!window.apiUrl) {
                    throw new Error('window.apiUrl is not defined');
                }

                // Initialize components
                await UsageStatistics.fetch();
                PlansManager.init();
                await URLHandler.handlePaymentCallback();

                console.log('Application initialized successfully');
            } catch (error) {
                console.error('Application initialization error:', error);
            }
        }
    };

    // Expose URLHandler.getQueryParams to global scope if needed
    window.getQueryParams = URLHandler.getQueryParams.bind(URLHandler);

    // Start the application
    App.init();
});

// // Authentication check
// document.addEventListener('DOMContentLoaded', function () {

//     if (typeof window.authRequired === 'function') {
//         window.authRequired();

//     } else {
//         console.warn('window.authRequired function not found');
//     }

// });

// EMAIL VERIFICATION:
/*
// Email Verification Handler
const EmailVerification = {
    showModal() {
        const modalElement = document.getElementById('verificationModal');
        if (!modalElement) {
            console.warn('Verification modal not found in DOM');
            return;
        }

        // Make modal non-dismissible
        const modal = new bootstrap.Modal(modalElement, {
            backdrop: 'static',
            keyboard: false
        });

        modal.show();

        // Attach resend event listener once
        const resendBtn = document.getElementById('resendVerification');
        if (resendBtn) {
            resendBtn.addEventListener('click', async () => {
                try {
                    resendBtn.disabled = true;
                    resendBtn.innerHTML = `
                        <span class="spinner-border spinner-border-sm" role="status"></span>
                        Sending...
                    `;

                    const response = await fetch(`${window.apiUrl}/users/resend-verification`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });

                    const data = await response.json();
                    alert(data.message || 'Verification email sent successfully.');

                } catch (error) {
                    console.error('Resend error:', error);
                    alert('Unable to resend verification email. Please try again later.');
                } finally {
                    resendBtn.disabled = false;
                    resendBtn.innerHTML = 'Resend Verification Email';
                }
            });
        }
    },

    async checkVerificationStatus() {
        try {
            // Fetch user data to determine if verified
            const response = await fetch(`${window.apiUrl}/users/check-verification-status`);
            const user = await response.json();

            if (user && user.valid_email === false) {
                console.log('User not verified — showing modal');
                this.showModal();
            } else {
                console.log('User verified or data missing.');
            }
        } catch (error) {
            console.error('Error checking verification status:', error);
        }
    }
};

// Initialize after main app
App.init().then(() => {
    EmailVerification.checkVerificationStatus();
});

// 
document.addEventListener("DOMContentLoaded", () => {
    if (window.user && window.user.valid_email === false) {
        EmailVerification.showModal();
    }
});


*/

// 
// emailVerification.js
const EmailVerification = {
  getUserFromToken() {
    const token = localStorage.getItem('access_token');
    if (!token || !isValidToken(token)) return null;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload; // includes email, username, name, etc.
    } catch (e) {
      console.error("Invalid token payload:", e);
      return null;
    }
  },

  showModal(user) {
    const modalEl = document.getElementById('verificationModal');
    if (!modalEl) return console.error('Verification modal missing.');

    // Insert name dynamically
    document.getElementById('verifyUserName').innerText = user?.name || user?.username || 'User';

    const modal = new bootstrap.Modal(modalEl, {
      backdrop: 'static',
      keyboard: false
    });
    modal.show();

    const resendBtn = document.getElementById('resendVerification');
    resendBtn.onclick = async () => {
      resendBtn.disabled = true;
      resendBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm" role="status"></span> Sending...
      `;
      try {
        const response = await fetch(`${window.apiUrl}/users/resend-verification`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
          }
        });
        const data = await response.json();
        window.response_modal(data.message || "Verification email sent successfully.");
      } catch (err) {
        console.error(err);
        window.response_modal("Failed to resend verification email. Try again later.");
      } finally {
        resendBtn.disabled = false;
        resendBtn.innerHTML = 'Resend Verification Email';
      }
    };
  },

  async checkVerificationStatus() {
    const user = this.getUserFromToken();
    if (!user) return console.log("No valid token found.");

    // Expecting `valid_email` claim in JWT payload
    if (user.valid_email === false) {
      console.log("Unverified user — showing modal");
      this.showModal(user);
    } else {
      console.log("User already verified.");
    }
  }
};

// Initialize after auth check
document.addEventListener('DOMContentLoaded', () => {
  EmailVerification.checkVerificationStatus();
});
