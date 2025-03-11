
document.addEventListener("DOMContentLoaded", () => {

        document.getElementById('signout-button').addEventListener('click', async function() {
            window.toggleButton(this, true, true); // Disable button
            try {
                const response = await window.make_request(`${window.apiUrl}/users/signout`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                const data = await response;

                if (response.success) {
                    // Logout successful, clear tokens from local storage
                    localStorage.removeItem('access_token'); 
                    localStorage.removeItem('refresh_token'); 
                    window.response_modal(`Signing-out: ${data.message}`);
                    window.location.href = data.redirect && data.redirect;        
                } else {
                    window.response_modal(`Signing-out: ${response.error}`);
                    window.location.href = data.redirect && data.redirect;
                }

            } catch (error) {
                console.error('During signout:', error);
                window.response_modal(`Signing-out - ${error}`);
            } finally {
                window.toggleButton(this, false, false); // Re-enable button after request completes
            }
        });
        });
        