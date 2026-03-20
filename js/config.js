// js/config.js  (Frontend)
window.APP_CONFIG = {
  // Flask (ราคาทองคำ/ข่าวสาร/ข้อมูลย้อนหลัง)
  PYTHON_API_URL: 'http://127.0.0.1:5000',
  PHP_API_BASE: 'api/api',
  // endpoint ของฝั่ง Flask (ใช้ประกอบ path)
  API: {
    THAI_PRICE: '/api/thai-gold-price',
    WORLD_PRICE: '/api/world-gold-price',
    NEWS: '/api/news',
    HISTORICAL: '/api/historical'
  }
};
