import axios from 'axios';
import { useAuthStore } from '../stores/authStore.js';
import { API_BASE_URL } from '../utils/constants.js';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60_000,
});

// Attach the JWT to every request.
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, drop the session so protected routes redirect to /login.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  },
);

export default client;
