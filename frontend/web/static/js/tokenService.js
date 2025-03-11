/*
// tokenService.js

const apiBaseUrl = `http://localhost:5000/api`;

// Set access and refresh tokens in localStorage
export const setTokens = (accessToken, refreshToken) => {
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
};

// Get the access token from localStorage
export const getAccessToken = () => {
    return localStorage.getItem("access_token");
};

// Get the refresh token from localStorage
export const getRefreshToken = () => {
    return localStorage.getItem("refresh_token");
};

// Clear tokens from localStorage (for logout)
export const clearTokens = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
};


// 
import axios from 'axios';
// import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './tokenService'; // this is already './tokenService'

// Create an Axios instance
const axiosInstance = axios.create({
    baseURL: apiBaseUrl,  // Your API base URL
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor to automatically attach the access token
axiosInstance.interceptors.request.use(
    (config) => {
        const accessToken = getAccessToken();
        if (accessToken) {
            config.headers['Authorization'] = `Bearer ${accessToken}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add a response interceptor to handle token expiration
axiosInstance.interceptors.response.use(
    response => response,
    async (error) => {
        if (error.response && error.response.status === 401) {
            // If the error is due to expired token, attempt token refresh
            const refreshToken = getRefreshToken();
            
            if (refreshToken) {
                try {
                    // Attempt to refresh the access token
                    const response = await axios.post(`{${apiBaseUrl}/refresh`, { refresh_token: refreshToken });

                    // Get the new access token from the response
                    const newAccessToken = response.data.access_token;

                    // Store the new access token in localStorage
                    setTokens(newAccessToken, refreshToken);

                    // Retry the original request with the new access token
                    error.config.headers['Authorization'] = `Bearer ${newAccessToken}`;
                    return axiosInstance(error.config);
                } catch (refreshError) {
                    // If refresh fails, clear tokens and force logout
                    clearTokens();
                    window.location.href = '/sigin';  // Redirect to login page
                    return Promise.reject(refreshError);
                }
            }
        }
        return Promise.reject(error);
    }
);

export default axiosInstance;

// Making API Requests with Axios Instance
// import axiosInstance from './axiosInstance';

const getProtectedData = async () => {
    try {
        const response = await axiosInstance.get('/protected');
        console.log('Protected data:', response.data);
    } catch (error) {
        console.error('Error fetching protected data:', error);
    }
};

// 4. Login Flow
// import { setTokens } from './tokenService';

const login = async (username, password) => {
    try {
        const response = await axios.post('/login', { username, password });
        const { access_token, refresh_token } = response.data;
        setTokens(access_token, refresh_token);
        window.location.href = '/dashboard';  // Redirect to the dashboard
    } catch (error) {
        console.error('Login failed:', error);
    }
};

// 5. Logout Flow:
// import { clearTokens } from './tokenService';

const logout = () => {
    clearTokens();
    window.location.href = '/signin';  // Redirect to login page
};

*/