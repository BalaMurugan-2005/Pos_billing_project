import axios from 'axios';

// Single backend: Django REST API (no more Spring Boot)
// Dev: VITE_API_URL=http://localhost:8000/api  (proxy via vite.config.js)
// Prod: VITE_API_URL=https://pos-django.onrender.com/api
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Auto-append trailing slash for Django compatibility (APPEND_SLASH=True by default).
// Without this, Django sends a 301 redirect which browsers follow as GET → causes 405 errors.
api.interceptors.request.use((config) => {
  if (config.url && !config.url.endsWith('/') && !config.url.includes('?')) {
    config.url = config.url + '/';
  }
  return config;
});
// Request interceptor — attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Track if a redirect is already in progress (avoid loops from background polling)
let isRedirectingToLogin = false;

// Response interceptor — handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (!isRedirectingToLogin) {
        isRedirectingToLogin = true;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setTimeout(() => {
          window.location.href = '/login';
          isRedirectingToLogin = false;
        }, 300);
      }
    }
    return Promise.reject(error);
  }
);

export default api;