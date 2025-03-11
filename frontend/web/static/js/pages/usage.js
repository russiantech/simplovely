document.addEventListener("DOMContentLoaded", () => {
    // Initialize the application
    initializeApp();
});

async function initializeApp() {
    // Fetch usage data on page load
    await fetchUsageData();

    // Set up event listeners
    setupEventListeners();
}

function setupEventListeners() {
    // Event listener for recording usage
    document.getElementById('recordUsageBtn').addEventListener('click', handleRecordUsage);

    // Event listener for submitting usage
    document.getElementById('submit_usage').addEventListener('click', handleSubmitUsage);
}

function handleRecordUsage() {
    const newUsageRow = document.getElementById('newUsageRow');
    newUsageRow.style.display = 'table-row';

    // Fetch and populate users
    fetchUsers();

    // Reset input fields
    document.getElementById('selectUser').value = '';
    document.getElementById('volumeUsed').value = '';
}

async function handleSubmitUsage() {
    const selectedUser = document.getElementById('selectUser').value;
    const volumeUsed = document.getElementById('volumeUsed').value;

    if (!selectedUser || !volumeUsed) {
        window.response_modal("Please select a user and enter volume used.");
        return; // Exit if validation fails
    }

    window.toggleButton(this, true, true); // Disable button

    const data = {
        subscription_id: null,
        user_id: selectedUser,
        units_used: volumeUsed,
    };

    try {
        const result = await make_request(`${window.apiUrl}/usage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        window.response_modal(result.message || result.error);
        await fetchUsageData(); // Refresh usage data after successful submission
    } catch (error) {
        window.response_modal(error, error.status);
        console.error('Error submitting usage:', error);
    } finally {
        window.toggleButton(this, false, false); // Re-enable button after request completes
    }
}

// Function to fetch usage data
async function fetchUsageData() {
    try {
        const data = await make_request(`${window.apiUrl}/usage?include_user=1`);
        const tableBody = document.querySelector('.table-list');

        // Clear existing rows except the first one
        const existingRows = tableBody.querySelectorAll('tr');
        existingRows.forEach((row, index) => {
            if (index > 0) {
                row.remove();
            }
        });

        // Populate the table with new data

        if(data.usage && data.usage.length > 0){
        data.usage.forEach((item, index) => {
            const row = `
                <tr>
                    <th class="order" scope="row">${index + 1}</th>
                    <th class="order" scope="row">${item.user.username}</th>
                    <td class="date">${new Date(item.created_at).toLocaleString()}</td>
                    <td class="status">${item.status}</td>
                    <td class="volume_used">${item.units_used}</td>
                    <td class="total_units text-nowrap">${item.total_units}</td>
                    <td class="remaining_units text-nowrap">${item.remaining_units}</td>
                </tr>
            `;

            tableBody.innerHTML += row;
        });

        }else{

            tableBody.innerHTML += `
                <tr>
                <td colspan='7'>
                    <span id="units-left" class="badge border-0 fs-xs text-danger text-bold rounded-pill">
                        No usage record found. Subscribe/recharge to enjoy and track usage here when you bring fabrics for laundry.
                    </span>
                </td>
                </tr>
        `
        }

    } catch (error) {
        console.error('Error fetching user usage:', error);
    }
}

// Function to fetch users
async function fetchUsers() {
    try {
        const data = await make_request(`${window.apiUrl}/users`);
        if (data.success) {
            const userSelect = document.getElementById('selectUser');
            userSelect.innerHTML = '<option value="">Select user...</option>'; // Reset options

            data.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id; // Use user ID as the value
                option.textContent = user.username || user.email; // Use username or email for display
                userSelect.appendChild(option);
            });
        } else {
            console.error('Failed to fetch users:', data.error);
        }
    } catch (error) {
        console.error('Error fetching users:', error);
    }
}
