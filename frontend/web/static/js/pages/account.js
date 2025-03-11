document.addEventListener("DOMContentLoaded", () => {

async function fetchUsageStatistics() {
    try {
        // Fetch the usage statistics from the server
        const data = await window.make_request(`${window.apiUrl}/usage/statistics`);
        
        if(data){

            // Update the units used display
            document.getElementById('units-used').innerText = `${data.units_used} units used of ${data.total_units}`;

            // Calculate and display the usage percentage, rounded to 2 decimal places
            const usagePercentage = Math.round(data.usage_percentage * 100) / 100;
            const usageProgressElement = document.getElementById('usage-progress');
            usageProgressElement.style.width = `${usagePercentage}%`;
            usageProgressElement.innerText = `${usagePercentage}%`;

            // Update aria attributes for accessibility
            usageProgressElement.setAttribute('aria-valuenow', usagePercentage);

            // Update the remaining units display
            document.getElementById('units-left').innerText = `Remaining ${data.remaining_units} units`;

            if(data.remaining_units <= 20){
                document.getElementById('units-left').classList.add('text-danger'); 
                document.getElementById('units-left').append('(Low units Alerts. Pls Recharge!!!)'); 
            }

        }

    } catch (error) {
        // Log error to the console and show a modal for the user
        console.error('Error fetching usage statistics:', error);
        window.response_modal('Error fetching usage statistics: ' + error.message);
    }
}

// Fetch usage statistics on page load
window.onload = fetchUsageStatistics();

// Function to format amount as currency
function formatCurrency(amount) {
    // Convert the amount to a number and format it
    const formattedAmount = amount.toLocaleString('en-NG', {
        style: 'currency',
        currency: 'NGN',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    //return formattedAmount.replace('₦', 'N'); // Replace the currency symbol for display
    return formattedAmount; // Replace the currency symbol for display
}

// Function to show/hide loading spinner
const toggleLoadingSpinner = (isLoading) => {
    const plansContainer = document.querySelector(".plans-container");
    if (isLoading) {
        // Show loading spinner
        plansContainer.innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>';
    } else {
        // Clear spinner
        plansContainer.innerHTML = '';
    }
};

// Fetch plans and handle the response
const fetch_plans = () => {
    const plansContainer = document.querySelector(".plans-container");

    // Check if the plansContainer exists
    if (!plansContainer) {
        console.warn("Plans container does not exist. Exiting fetchPlans.");
        return; // Exit the function if the container is not found
    }

    // Show loading spinner
    toggleLoadingSpinner(true);

    fetch(`${window.apiUrl}/plans`)
        .then(response => response.json())
        .then(data => {
            // Remove loading spinner
            toggleLoadingSpinner(false);

            if (data.success && data.plans) {
                data.plans.forEach(plan => {
                    const planRow = `
                                <tr class="cursor-pointer">
                                    <td class="py-3 ps-0">
                                        <div class="d-flex align-items-start align-items-md-center">
                                            <div class="ratio bg-body-secondary rounded-2 overflow-hidden flex-shrink-0" style="width: 66px">
                                                <img src="static/img/account/products/03.jpg" class="hover-effect-target" alt="Image">
                                            </div>
                                            <div class="ps-2 ms-1">
                                                <h6 class="product mb-1 mb-md-0">
                                                    <span class="fs-sm fw-medium">${plan.name}</span>
                                                </h6>
                                            </div>
                                        </div>
                                    </td>
                                    <td class="d-none d-md-table-cell py-3">
                                        <span class="badge fs-xs text-info bg-info-subtle rounded-pill">${formatCurrency(plan.amount)}</span>
                                    </td>
                                    <td class="text-end d-none d-sm-table-cell py-3">${plan.units || 'N/A'}</td>
                                    <td class="text-end py-3">
                                        <button class="btn btn-sm btn-dark rounded-pill subscribe-btn" data-plan-id="${plan.id}">Recharge</button>
                                    </td>
                                </tr>`;

                    plansContainer.insertAdjacentHTML('beforeend', planRow);
                });

                // Event listener for subscribe buttons
                plansContainer.addEventListener('click', (event) => {
                    if (event.target.classList.contains('subscribe-btn')) {
                        const button = event.target;
                        const planId = button.dataset.planId;
                        const email = null;

                        //
                        // Call subscribeUser with button reference
                        subscribeUser(planId, email, button);
                        //
                    }
                });

            } else {
                window.response_modal("Failed to load plans.");
            }
        })
        .catch(() => {
            // Remove loading spinner on error
            toggleLoadingSpinner(false);
            window.response_modal("Error fetching plans.");
        });
};

// Call fetchPlans to initiate fetching
fetch_plans();

// Email validation function
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

// Function to handle subscription
function subscribeUser(planId, email, button) {
    // Disable the button and show loading spinner
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';

    // Create the request body as an object
    const requestBody = {
        email: email
    };

    window.make_request(`${window.apiUrl}/payment/${planId}/paystack`, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'Client-Callback-Url': window.location.href,
        },
        body: JSON.stringify(requestBody), // Use the object here
    })
    .then(response => {
        // Re-enable button after response
        button.disabled = false;

        if (response.success) {
            window.location.href = response.redirect;
        } else {
            button.innerHTML = 'Subscribe'; // Reset button text
            window.response_modal(response.error || "Error processing payment");
        }
    })
    .catch(error => {
        // Re-enable button on error
        button.disabled = false;
        button.innerHTML = 'Subscribe'; // Reset button text
        window.response_modal(`Error: ${error.message || error + " unknown-err"}`);
    });
}

// Verify a transaction
const getQueryParams = () => {
    const params = new URLSearchParams(window.location.search);
    return {
        status: params.get('status'), // Get the 'status' parameter
        reference: params.get('reference') || params.get('trxref') // Get 'reference' or 'trxref'
    };
};

window.getQueryParams = getQueryParams;

//
function removeQueryParameters() {
    const url = window.location.href; // Get the current URL
    const baseUrl = url.split('?')[0]; // Get the base URL

    // Use history.replaceState to update the URL without reloading the page
    window.history.replaceState({}, document.title, baseUrl);
}

// See usage
//removeQueryParameters();
//console.log('Query parameters removed from URL');

const queryParams = getQueryParams();
//  console.log("queryParams->", queryParams)
if (queryParams.reference) {
    window.response_modal(`Verifying your transaction, please wait...`);
    fetch(`${window.apiUrl}/payment/callback/paystack?reference=${queryParams.reference}`)
        .then(response => response.json())
        .then(result => {
            console.log("result", result, window.location.href);
            window.response_modal(result.success ? result.message || "Transaction completed successfully!" : result.error || "Error processing transaction.");
            removeQueryParameters();
            //return location.reload();
        })
        .catch(error => {
            window.response_modal(`Error: ${error.message || "Unknown error occurred."}`);
        });
}

});


document.addEventListener('DOMContentLoaded', function () {
    window.authRequired();
});