// js/config.js  (Frontend)
const _isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname);

function normalizeBaseUrl(url) {
  return String(url || '').trim().replace(/\/+$/, '');
}

const _explicitApiUrl =
  window.__APP_API_URL__ ||
  document.documentElement?.dataset?.apiBase;

const _pythonApiUrl = _isLocalhost
  ? 'http://127.0.0.1:5000'
  : normalizeBaseUrl(_explicitApiUrl || window.location.origin);

window.APP_CONFIG = {
  // Flask (ราคาทองคำ/ข่าวสาร/ข้อมูลย้อนหลัง)
  PYTHON_API_URL: _pythonApiUrl,
  PHP_API_BASE: 'api/api',
  // endpoint ของฝั่ง Flask (ใช้ประกอบ path)
  API: {
    THAI_PRICE: '/api/thai-gold-price',
    WORLD_PRICE: '/api/world-gold-price',
    NEWS: '/api/news',
    HISTORICAL: '/api/historical'
  }
};
