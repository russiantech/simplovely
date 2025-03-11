document.addEventListener("DOMContentLoaded", () => {   
    /*
    fetch(`${window.apiUrl}/usage?include_user=1`)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        const tableBody = document.querySelector('.table-list');
        
        // Clear existing rows but keep the first row (for creating new records)
        const existingRows = tableBody.querySelectorAll('tr');
        
        // Remove all rows except the first one
        existingRows.forEach((row, index) => {
            if (index > 0) {
                row.remove();
            }
        });

        // Use forEach with correct parameters
        data.usage.forEach((item, index) => {
            const row = `
                <tr>
                    <th class="order" scope="row">${index + 1}</th>
                    <th class="order" scope="row">${item.user.username}</th>
                    <td class="date">${new Date(item.created_at).toLocaleString()}</td>
                    <td class="status">${item.status}</td>
                    <td class="volume_used">${item.units_used}</td>
                    <td class="phone text-nowrap">${item.total_units}</td>
                    <td class="phone text-nowrap">${item.remaining_units}</td>
                </tr>
            `;
            tableBody.innerHTML += row;
        });
    })
    .catch(error => console.error('Error fetching user usage:', error));
    

    document.getElementById('recordUsageBtn').addEventListener('click', function () {

        document.getElementById('newUsageRow').style.display = 'table-row';
        // const newUsageRow = document.getElementById('newUsageRow');
        // newUsageRow.style.display = 'table-row';

        // Fetch and populate users
        fetchUsers();

        // Optionally reset the input fields
        document.getElementById('selectUser').value = '';
        document.getElementById('volumeUsed').value = '';
        //
        document.getElementById('submit_usage').addEventListener('click', function (event) {
            event.preventDefault();  // Prevent the form from submitting normally
        
            alert(true);
            const selectedUser = document.getElementById('selectUser').value;
            const volumeUsed = document.getElementById('volumeUsed').value;
        
            if (!selectedUser || !volumeUsed) {
                alert('Please select a user and input the volume used');
                return;
            }
        
            window.toggleButton(this, true, true); // Disable button and start spinner
        
            const data = {
                subscription_id: null,
                user_id: selectedUser,
                units_used: volumeUsed,
            };
        
            fetch(`${window.apiUrl}/usage`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            })
            .then(response => response.json())
            .then(result => {
                window.response_modal(result.message || result.error);
            })
            .catch(error => {
                console.error('Error submitting usage:', error);
                window.response_modal('An error occurred. Please try again.');
            })
            .finally(() => {
                // Regardless of success or failure, remove the spinning effect and re-enable the button
                window.toggleButton(this, false, false);
            });
    
        });
        

    });

    function fetchUsers() {

        fetch(`${window.apiUrl}/users`) // Adjust the URL to your backend API endpoint
            .then(response => response.json())
            .then(data => {
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
            })
            .catch(error => console.error('Error fetching users:', error));
    }
    */
    /*
    document.getElementById('submit_usage').addEventListener('click', function (event) {
        event.preventDefault();  // Prevent the form from submitting normally
    
        alert(true);
        const selectedUser = document.getElementById('selectUser').value;
        const volumeUsed = document.getElementById('volumeUsed').value;
    
        if (!selectedUser || !volumeUsed) {
            alert('Please select a user and input the volume used');
            return;
        }
    
        window.toggleButton(this, true, true); // Disable button and start spinner
    
        const data = {
            subscription_id: null,
            user_id: selectedUser,
            units_used: volumeUsed,
        };
    
        fetch(`${window.apiUrl}/usage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        })
        .then(response => response.json())
        .then(result => {
            window.response_modal(result.message || result.error);
        })
        .catch(error => {
            console.error('Error submitting usage:', error);
            window.response_modal('An error occurred. Please try again.');
        })
        .finally(() => {
            // Regardless of success or failure, remove the spinning effect and re-enable the button
            window.toggleButton(this, false, false);
        });

    });*/
    
});

//
document.addEventListener("DOMContentLoaded", () => {
    // Fetch usage data on page load
    fetchUsageData();

    // Event listener for recording usage
    document.getElementById('recordUsageBtn').addEventListener('click', () => {
        const newUsageRow = document.getElementById('newUsageRow');
        newUsageRow.style.display = 'table-row';

        // Fetch and populate users
        fetchUsers();

        // Reset input fields
        document.getElementById('selectUser').value = '';
        document.getElementById('volumeUsed').value = '';
        //
            // Event listener for submitting usage
    document.getElementById('submit_usage').addEventListener('click', async function () {
        const selectedUser = document.getElementById('selectUser').value;
        const volumeUsed = document.getElementById('volumeUsed').value;

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
        } catch (error) {
            window.response_modal(error);
            console.error('Error submitting usage:', error);
        } finally {
            window.toggleButton(this, false, false); // Re-enable button after request completes
        }
        
    });

    });

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
});
