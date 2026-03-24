// js/config.js  (Frontend)
const _isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
const _searchParams = new URLSearchParams(window.location.search);
const _legacyLocalMode = _isLocalhost && _searchParams.get('legacy_local') === '1';
const _forceLocalApi = window.__APP_FORCE_LOCAL__ === true || _legacyLocalMode;
const _disableSw = window.__APP_DISABLE_SW__ === true || _legacyLocalMode;

function normalizeBaseUrl(url) {
  return String(url || '').trim().replace(/\/+$/, '');
}

function isPlaceholderApiUrl(url) {
  const normalized = normalizeBaseUrl(url).toLowerCase();
  return !normalized || normalized.includes('your-render-api.onrender.com');
}

const _explicitApiUrl =
  window.__APP_API_URL__ ||
  document.documentElement?.dataset?.apiBase;

const _localPythonApiUrl = normalizeBaseUrl(window.__APP_LOCAL_API_URL__ || 'http://127.0.0.1:5000');

const _pythonApiUrl = (_isLocalhost || _forceLocalApi)
  ? _localPythonApiUrl
  : normalizeBaseUrl(
      isPlaceholderApiUrl(_explicitApiUrl) ? window.location.origin : _explicitApiUrl
    );

window.APP_CONFIG = {
  // Flask (ราคาทองคำ/ข่าวสาร/ข้อมูลย้อนหลัง)
  PYTHON_API_URL: _pythonApiUrl,
  PHP_API_BASE: 'api/api',
  LEGACY_LOCAL_MODE: _legacyLocalMode,
  DISABLE_SW: _disableSw,
  // endpoint ของฝั่ง Flask (ใช้ประกอบ path)
  API: {
    THAI_PRICE: '/api/thai-gold-price',
    WORLD_PRICE: '/api/world-gold-price',
    NEWS: '/api/news',
    HISTORICAL: '/api/historical'
  }
};
