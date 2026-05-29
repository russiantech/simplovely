// signout.js
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('signout-button');
    if (!btn) return;

    btn.addEventListener('click', async function () {
        window.toggleButton(this, true);
        try {
            const data = await window.make_request(`${window.apiUrl}/users/signout`, {
                method: 'POST',
            });

            // Clear local tokens regardless of API response
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');

            if (data && data.success) {
                window.response_modal(data.message || 'Signed out successfully.', 'success');
                setTimeout(() => {
                    window.location.href = data.redirect || '/signin';
                }, 1200);
            } else {
                // Still redirect even if the API call wasn't clean
                window.location.href = '/signin';
            }
        } catch (_) {
            // Sign out locally even if the API call fails
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/signin';
        }
    });
});
