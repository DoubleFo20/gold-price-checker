import io

with io.open('script.js', 'r', encoding='utf-8') as f:
    text = f.read()

replacements = {
    '${window.APP_CONFIG.PHP_API_BASE} /alerts/list.php': '${window.APP_CONFIG.PHP_API_BASE}/alerts/list.php',
    '${window.APP_CONFIG.PHP_API_BASE} /alerts/delete.php': '${window.APP_CONFIG.PHP_API_BASE}/alerts/delete.php',
    '${window.APP_CONFIG.PHP_API_BASE} /auth/update_profile.php': '${window.APP_CONFIG.PHP_API_BASE}/auth/update_profile.php',
    '${window.APP_CONFIG.PHP_API_BASE} /auth/change_password.php': '${window.APP_CONFIG.PHP_API_BASE}/auth/change_password.php',
    '${window.APP_CONFIG.PHP_API_BASE} /alerts/create.php': '${window.APP_CONFIG.PHP_API_BASE}/alerts/create.php',
    '${window.APP_CONFIG.PYTHON_API_URL} /api/thai - gold - price': '${window.APP_CONFIG.PYTHON_API_URL}/api/thai-gold-price',
    '${window.APP_CONFIG.PYTHON_API_URL} /api/world - gold - price': '${window.APP_CONFIG.PYTHON_API_URL}/api/world-gold-price',
    '${window.APP_CONFIG.PYTHON_API_URL} /api/historical ? days = ${days} ': '${window.APP_CONFIG.PYTHON_API_URL}/api/historical?days=${days}',
    '${window.APP_CONFIG.PHP_API_BASE} /proxy/news.php ? q = gold + investment': '${window.APP_CONFIG.PHP_API_BASE}/proxy/news.php?q=gold+investment',
    '${window.APP_CONFIG.PYTHON_API_URL} /api/forecast ? period = ${period}& model=${model}& hist_days=${histDays} ': '${window.APP_CONFIG.PYTHON_API_URL}/api/forecast?period=${period}&model=${model}&hist_days=${histDays}',
    'data - alert - id=': 'data-alert-id=',
    '< div class=': '<div class=',
    '</div >': '</div>',
    '< p class=': '<p class=',
    '</p >': '</p>',
    '${window.APP_CONFIG.PHP_API_BASE} /user/save_forecast.php': '${window.APP_CONFIG.PHP_API_BASE}/user/save_forecast.php',
    '${window.APP_CONFIG.PHP_API_BASE} /user/get_saved_forecasts.php': '${window.APP_CONFIG.PHP_API_BASE}/user/get_saved_forecasts.php'
}

for k, v in replacements.items():
    text = text.replace(k, v)

with io.open('script.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("Patch applied to script.js")
