// js/config.js  (Frontend)
// Standardized API configuration - Legacy PHP scripts deprecated, unified Flask backend

const _isLocalhost = ["localhost", "127.0.0.1"].includes(
  window.location.hostname,
);
const _searchParams = new URLSearchParams(window.location.search);
// Legacy PHP mode is permanently deprecated; all endpoints route to Flask
const _legacyLocalMode = false;
const _disableSw = window.__APP_DISABLE_SW__ === true;

function normalizeBaseUrl(url) {
  return String(url || "")
    .trim()
    .replace(/\/+$/, "");
}

function isPlaceholderApiUrl(url) {
  const normalized = normalizeBaseUrl(url).toLowerCase();
  return !normalized || normalized.includes("your-render-api.onrender.com");
}

const _explicitApiUrl =
  window.__APP_API_URL__ || document.documentElement?.dataset?.apiBase;

// If running directly on Flask (port 5000) or production origin, relative base is preferred
const _isFlaskDirect = window.location.port === "5000";

const _localPythonApiUrl = normalizeBaseUrl(
  window.__APP_LOCAL_API_URL__ || (_isFlaskDirect ? "" : "http://127.0.0.1:5000"),
);

let _pythonApiUrl = normalizeBaseUrl(
  _explicitApiUrl && !isPlaceholderApiUrl(_explicitApiUrl)
    ? _explicitApiUrl
    : (_isLocalhost ? _localPythonApiUrl : "")
);

// Standardize all API calls to unified Flask endpoints
// When frontend is served from same origin or Flask direct, relative paths are used
const _apiPrefix = _pythonApiUrl ? `${_pythonApiUrl}/api` : "/api";
const _phpApiBase = _pythonApiUrl ? `${_pythonApiUrl}/api/api` : "/api/api";

window.APP_CONFIG = {
  // Flask unified backend
  PYTHON_API_URL: _pythonApiUrl,
  API_BASE: _apiPrefix,
  PHP_API_BASE: _phpApiBase,
  LEGACY_LOCAL_MODE: false,
  DISABLE_SW: _disableSw,
  // Standardized Flask API endpoints (relative paths to avoid double-origin in buildPythonApiUrl)
  API: {
    THAI_PRICE: "/api/thai-gold-price",
    WORLD_PRICE: "/api/world-gold-price",
    NEWS: "/api/news",
    HISTORICAL: "/api/historical",
    INTRADAY: "/api/intraday",
    FORECAST: "/api/forecast",
    AUTH_LOGIN: "/api/auth/login",
    AUTH_REGISTER: "/api/auth/register",
    AUTH_CHECK_SESSION: "/api/auth/check-session",
    AUTH_CHANGE_PASSWORD: "/api/auth/change-password",
    AUTH_LOGOUT: "/api/auth/logout",
    ALERTS_CREATE: "/api/alerts/create",
    ALERTS_LIST: "/api/alerts",
  },
};
