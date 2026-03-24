// --- HARD FIX ---
if (typeof sw === 'undefined') var sw = null;

/* ===========================
   Loader: โหลด Components
   =========================== */
async function loadComponent(url, targetId) {
    const el = document.getElementById(targetId);
    if (!el) return;
    try {
        const cacheBuster = new Date().getTime();
        const resp = await fetch(`components/${url}?v=${cacheBuster}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        el.innerHTML = await resp.text();
    } catch (e) {
        console.error('Load error:', url, e);
        el.innerHTML = `<p style="color:red; text-align:center;">โหลดส่วนประกอบ ${url} ล้มเหลว</p>`;
    }
}

async function loadAllComponents() {
    await Promise.all([
        loadComponent('0-hero-section.html', 'hero-container'),
        loadComponent('1-price-today.html', 'price-today-container'),
        loadComponent('2-live-chart.html', 'live-chart-container'),
        loadComponent('3-historical-chart.html', 'historical-chart-container'),
        loadComponent('4-news.html', 'news-container-placeholder'),
        loadComponent('5-calculator.html', 'calculator-container'),
        loadComponent('6-forecast.html', 'forecast-container'),
        loadComponent('7-alerts.html', 'alerts-container')
    ]);
}

let isLoggedIn = false;
let currentUser = null;
let chartThai, chartWorld, forecastChart;
let latestThaiPrices = {};


function showLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.style.display = 'flex';
    document.body.classList.add('modal-open');
    setAuthMode('login');
}
function hideLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.style.display = 'none';
    document.body.classList.remove('modal-open');
}
function setAuthMode(mode) {
    const modalContainer = document.querySelector('#loginModal .modal-container');
    if (!modalContainer) return;
    const titleEl = document.getElementById('auth-header-title');

    // Reset all states
    modalContainer.classList.remove('right-panel-active', 'forgot-panel-active');

    if (mode === 'register') {
        modalContainer.classList.add('right-panel-active');
        if (titleEl) titleEl.textContent = 'สร้างบัญชีใหม่';
    } else if (mode === 'forgot') {
        modalContainer.classList.add('forgot-panel-active');
        if (titleEl) titleEl.textContent = 'รีเซ็ตรหัสผ่าน';
    } else {
        if (titleEl) titleEl.textContent = 'ยินดีต้อนรับกลับมา';
    }
}


// (ค้นหาและแทนที่ฟังก์ชัน login เดิม)
async function login() {
    const email = document.getElementById('login-email')?.value;
    const password = document.getElementById('login-password')?.value;
    if (!email || !password) return alert('กรุณากรอกอีเมลและรหัสผ่าน');

    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/auth/login.php`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (!res.ok || !data.success) {
            throw new Error(data.message || 'อีเมลหรือรหัสผ่านไม่ถูกต้อง');
        }

        hideLoginModal();
        alert('เข้าสู่ระบบสำเร็จ!');

        // [แก้ไข] ตรวจสอบ Role และ Redirect
        if (data.user && data.user.role === 'admin') {
            window.location.href = 'api/admin/'; // Redirect ไปหน้า Admin
        } else {
            // สำหรับ User ทั่วไป ให้ตรวจสอบ Session ใหม่เพื่ออัปเดตหน้าเว็บ
            await checkSession();
        }

    } catch (error) {
        console.error('Login failed:', error);
        alert(error.message);
    }
}

async function register() {
    const name = document.getElementById('register-name')?.value;
    const email = document.getElementById('register-email')?.value;
    const password = document.getElementById('register-password')?.value;
    if (!name || !email || !password) return alert('กรุณากรอกข้อมูลให้ครบถ้วน');

    try {
        const response = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/auth/register.php`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.message || 'เกิดข้อผิดพลาดในการสมัครสมาชิก');
        }

        alert(data.message);
        setAuthMode('login');

    } catch (error) {
        console.error('Register error:', error);
        alert(error.message);
    }
}

function togglePasswordField(targetId, btn) {
    const input = document.getElementById(targetId);
    if (!input) return;
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    const icon = btn?.querySelector('i');
    if (icon) {
        icon.classList.toggle('fa-eye', !show);
        icon.classList.toggle('fa-eye-slash', show);
    }
}

function setupPasswordToggles() {
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', () => togglePasswordField(btn.dataset.target, btn));
    });
}

// Old toggleForgotPasswordForm removed as it's replaced by setAuthMode('forgot')

async function submitForgotPassword() {
    const emailInput = document.getElementById('forgot-email');
    const statusEl = document.getElementById('forgot-status');
    const email = emailInput?.value?.trim();
    if (!email) {
        if (statusEl) statusEl.textContent = 'กรุณากรอกอีเมล';
        return;
    }
    if (statusEl) statusEl.textContent = 'กำลังส่งลิงก์รีเซ็ตรหัสผ่าน...';
    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/auth/forgot.php`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.message || 'ส่งลิงก์ไม่สำเร็จ');
        }
        if (statusEl) statusEl.textContent = 'ส่งลิงก์ตั้งรหัสผ่านแล้ว';
    } catch (err) {
        if (statusEl) statusEl.textContent = err.message || 'เกิดข้อผิดพลาด';
    }
}

async function checkSession() {
    try {
        const url = `${window.APP_CONFIG.PHP_API_BASE}/auth/check_session.php`;
        const response = await fetch(url, { method: 'POST', credentials: 'include' });
        const data = await response.json();
        if (data.success && data.authenticated && data.user) {
            window.isLoggedIn = true;
            window.currentUser = data.user;
            isLoggedIn = true;
            currentUser = data.user;
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('currentUser', JSON.stringify(data.user));
            // Store email for Python API calls
            window.userEmail = data.user.email;
            localStorage.setItem('user_email', data.user.email);
        } else {
            window.isLoggedIn = false;
            window.currentUser = null;
            isLoggedIn = false;
            currentUser = null;
            localStorage.removeItem('isLoggedIn');
            localStorage.removeItem('currentUser');
            localStorage.removeItem('user_email');
            window.userEmail = null;
        }
    } catch (error) {
        console.error('❌ Check session error:', error);
        window.isLoggedIn = false;
        window.currentUser = null;
        isLoggedIn = false;
        currentUser = null;
        localStorage.removeItem('user_email');
        window.userEmail = null;
    } finally {
        updateUIAfterLogin();
    }
}

async function logout() {
    if (!confirm('ต้องการออกจากระบบ?')) return;
    try {
        await fetch(`${window.APP_CONFIG.PHP_API_BASE}/auth/logout.php`, { method: 'POST', credentials: 'include' });
    } finally {
        window.isLoggedIn = false;
        window.currentUser = null;
        isLoggedIn = false;
        currentUser = null;
        localStorage.clear();
        window.userEmail = null; // Clear user email on logout
        window.location.reload();
    }
}

function loadUserFromStorage() {
    // ตรวจสอบและล้างข้อมูลล็อกอินเก่า (สำหรับการพัฒนา)
    if (window.location.search.includes('clear=true') || localStorage.getItem('force_logout') === 'true') {
        localStorage.clear();
        sessionStorage.clear();
        localStorage.removeItem('force_logout');
        console.log('🧹 Login data cleared!');
        return;
    }

    const savedLogin = localStorage.getItem('isLoggedIn');
    const savedUser = localStorage.getItem('currentUser');
    const savedEmail = localStorage.getItem('user_email');
    if (savedLogin === 'true' && savedUser) {
        try {
            window.isLoggedIn = true;
            window.currentUser = JSON.parse(savedUser);
            isLoggedIn = true;
            currentUser = window.currentUser;
            window.userEmail = savedEmail;
        } catch (e) {
            localStorage.clear();
            window.isLoggedIn = false;
            window.currentUser = null;
            isLoggedIn = false;
            currentUser = null;
            window.userEmail = null;
        }
    }
}

function updateUIAfterLogin() {
    const loginMenu = document.getElementById('login-menu-container');
    const userMenu = document.getElementById('user-menu-container');
    const notifMenu = document.getElementById('notification-menu-container');
    const usernameDisplay = document.getElementById('username-display');

    if (window.isLoggedIn && window.currentUser) {
        if (loginMenu) loginMenu.style.display = 'none';
        if (userMenu) userMenu.style.display = 'list-item';
        if (notifMenu) {
            notifMenu.style.display = 'list-item';
            fetchNotifications(); // โหลดแจ้งเตือนทันทีที่ล็อกอิน
        }
        if (usernameDisplay) {
            usernameDisplay.textContent = window.currentUser.name || 'ผู้ใช้';
        }
    } else {
        if (loginMenu) loginMenu.style.display = 'list-item';
        if (userMenu) userMenu.style.display = 'none';
        if (notifMenu) notifMenu.style.display = 'none';
        hideProfileModal();
    }

    const show = (elId, show) => {
        const el = document.getElementById(elId);
        if (el) el.style.display = show ? 'block' : 'none';
    };
    show('calculator-login-required', !window.isLoggedIn);
    show('calculator-tool', window.isLoggedIn);
    show('alert-login-required', !window.isLoggedIn);
    show('alert-tool', window.isLoggedIn);
    show('forecast-login-required', !window.isLoggedIn);
    show('forecast-tool', window.isLoggedIn);

    if (window.isLoggedIn && window.currentUser) {
        const emailInput = document.getElementById('user-email');
        if (emailInput && !emailInput.value) {
            emailInput.value = window.currentUser.email || '';
        }
    }
    loadAlertsList();
}

function showProfileModal() {
    if (!window.isLoggedIn) {
        showLoginModal();
        return;
    }
    const modal = document.getElementById('profileModal');
    if (!modal) return;

    // กรอกข้อมูลผู้ใช้
    const nameInput = document.getElementById('profile-name-input');
    const emailInput = document.getElementById('profile-email-input');
    if (nameInput) nameInput.value = window.currentUser?.name || '';
    if (emailInput) emailInput.value = window.currentUser?.email || '';

    // รีเซ็ต status messages
    const nameStatus = document.getElementById('profile-name-status');
    const pwStatus = document.getElementById('profile-password-status');
    if (nameStatus) nameStatus.textContent = '';
    if (pwStatus) pwStatus.textContent = '';

    // รีเซ็ต password fields
    ['profile-old-password', 'profile-new-password', 'profile-confirm-password'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });

    // เปิด tab แรก
    switchProfileTab('info', document.querySelector('.profile-tab'));

    // โหลดรายการแจ้งเตือน
    loadProfileAlerts();
    
    // [เพิ่ม] โหลดสถานะ LINE
    loadLineStatus();
    
    // [เพิ่ม] โหลดสถานะ Push
    loadPushStatus();

    modal.classList.add('show');
}

function hideProfileModal() {
    const modal = document.getElementById('profileModal');
    if (modal) modal.classList.remove('show');
}

function switchProfileTab(tabName, btn) {
    document.querySelectorAll('.profile-tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.profile-tab').forEach(el => el.classList.remove('active'));
    const target = document.getElementById('profile-tab-' + tabName);
    if (target) target.classList.add('active');
    if (btn) btn.classList.add('active');

    if (tabName === 'forecasts') {
        loadProfileForecasts();
    }
}

async function saveForecast() {
    if (!window.isLoggedIn || !window.latestForecastData) return;
    const btn = document.getElementById('save-forecast-btn');
    const statusMsg = document.getElementById('save-forecast-status');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> กำลังบันทึก...';

    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/user/save_forecast.php`, {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(window.latestForecastData)
        });

        let rawText = '';
        try { rawText = await res.text(); } catch (e) { }

        let data = {};
        try { data = JSON.parse(rawText); } catch (e) { }

        if (!res.ok || !data.success) {
            console.error("Save Forecast raw response:", rawText);
            throw new Error(data.message || 'บันทึกไม่สำเร็จ (' + rawText.substring(0, 50) + ')');
        }

        statusMsg.style.color = 'var(--success-color, #4CAF50)';
        statusMsg.textContent = data.message || 'บันทึกสำเร็จ!';
        btn.style.display = 'none'; // ซ่อนปุ่มหลังบันทึกเสร็จ
    } catch (err) {
        statusMsg.style.color = 'var(--brand-gold)';
        statusMsg.textContent = 'เกิดข้อผิดพลาด: ' + err.message;
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> ลองอีกครั้ง';
    }
}

async function loadProfileForecasts() {
    const listEl = document.getElementById('profile-forecasts-list');
    if (!listEl) return;
    if (!window.isLoggedIn) { listEl.innerHTML = ''; return; }

    listEl.innerHTML = '<p class="profile-loading">กำลังโหลดประวัติ...</p>';
    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/user/get_saved_forecasts.php`, {
            method: 'GET', credentials: 'include'
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) throw new Error(data.message || 'โหลดไม่สำเร็จ');
        renderProfileForecasts(data.data || []);
    } catch (err) {
        listEl.innerHTML = `<p class="profile-alert-empty">โหลดรายการไม่สำเร็จ: ${err.message}</p>`;
    }
}

function renderProfileForecasts(items) {
    const listEl = document.getElementById('profile-forecasts-list');
    if (!listEl) return;
    if (!items.length) {
        listEl.innerHTML = '<p class="profile-alert-empty">ยังไม่มีประวัติการบันทึกคำพยากรณ์</p>';
        return;
    }
    const fmtDate = (v) => {
        if (!v) return '-';
        const dateStr = v.includes('T') || v.includes(' ') ? v : v + 'T00:00:00';
        const d = new Date(dateStr);
        return isNaN(d.getTime()) ? v : d.toLocaleDateString('th-TH');
    };
    const fmtMoney = v => Number(v).toLocaleString('th-TH', { minimumFractionDigits: 2 });

    const todayStr = new Date().toISOString().slice(0, 10);

    listEl.innerHTML = items.map(item => {
        const targetDate = (item.target_date || '').slice(0, 10);
        const isVerified = !!item.verified_at;
        const isPast = targetDate <= todayStr;

        // กำหนดสถานะ
        let statusBadge = '';
        let comparisonHTML = '';

        if (isVerified && item.actual_max_price != null) {
            // ตรวจสอบว่าราคาจริงอยู่ในช่วงพยากรณ์หรือไม่
            const actualMax = parseFloat(item.actual_max_price);
            const actualMin = parseFloat(item.actual_min_price);
            const predMax = parseFloat(item.max_price);
            const predMin = parseFloat(item.min_price);

            // ราคาจริง (bar_sell) อยู่ในช่วง [min_price, max_price] ของพยากรณ์
            const inRange = actualMax <= predMax && actualMin >= predMin;

            if (inRange) {
                statusBadge = '<span class="profile-alert-badge done" style="margin:0; background:#16A085;">✅ ถูกต้อง</span>';
            } else {
                statusBadge = '<span class="profile-alert-badge done" style="margin:0; background:#e74c3c;">❌ ผิดพลาด</span>';
            }

            comparisonHTML = `
                <div style="margin-top: 10px; padding: 10px; border-radius: 8px; background: ${inRange ? 'rgba(22,160,133,0.1)' : 'rgba(231,76,60,0.1)'}; border: 1px solid ${inRange ? 'rgba(22,160,133,0.3)' : 'rgba(231,76,60,0.3)'};">
                    <div style="font-weight: bold; margin-bottom: 6px; color: ${inRange ? '#16A085' : '#e74c3c'};">
                        📊 ราคาจริง ณ วันที่ ${fmtDate(item.target_date)}
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.88rem;">
                        <div><strong>ราคาขาย (จริง):</strong> ฿${fmtMoney(actualMax)}</div>
                        <div><strong>ราคารับซื้อ (จริง):</strong> ฿${fmtMoney(actualMin)}</div>
                        <div><strong>ราคามากสุด (พยากรณ์):</strong> ฿${fmtMoney(predMax)}</div>
                        <div><strong>ราคาน้อยสุด (พยากรณ์):</strong> ฿${fmtMoney(predMin)}</div>
                    </div>
                    <div style="margin-top: 6px; font-size: 0.82rem; color: #888;">ตรวจสอบเมื่อ: ${fmtDate(item.verified_at)}</div>
                </div>`;
        } else if (isPast) {
            statusBadge = '<span class="profile-alert-badge waiting" style="margin:0; background:#f39c12;">⏳ รอตรวจสอบ</span>';
            comparisonHTML = `
                <div style="margin-top: 10px; padding: 8px; border-radius: 6px; background: rgba(243,156,18,0.08); border: 1px solid rgba(243,156,18,0.2); font-size: 0.85rem; color: #f39c12;">
                    ⏳ ถึงวัน target แล้ว — กำลังรอระบบดึงราคาจริงมาเทียบอัตโนมัติ
                </div>`;
        } else {
            statusBadge = `<span class="profile-alert-badge done" style="margin: 0;">${item.trend}</span>`;
            comparisonHTML = `
                <div style="margin-top: 10px; padding: 8px; border-radius: 6px; background: rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.08); font-size: 0.85rem; color: #888;">
                    🔮 รอถึงวันที่ ${fmtDate(item.target_date)} เพื่อเปรียบเทียบ
                </div>`;
        }

        return `
            <div class="profile-alert-item" style="flex-direction: column; align-items: flex-start; gap: 8px;">
                <div style="display: flex; justify-content: space-between; width: 100%; border-bottom: 1px solid #444; padding-bottom: 8px;">
                    <div class="profile-alert-title">\u23F3 พยากรณ์สำหรับวันที่: ${fmtDate(item.target_date)}</div>
                    ${statusBadge}
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; width: 100%; gap: 10px; font-size: 0.9rem; margin-top: 5px;">
                    <div><strong>ราคามากสุด:</strong> ฿${fmtMoney(item.max_price)}</div>
                    <div><strong>ราคาน้อยสุด:</strong> ฿${fmtMoney(item.min_price)}</div>
                    <div><strong>แม่นยำ (R²):</strong> ${item.confidence}%</div>
                    <div><strong>ข้อมูลฝึกฝน:</strong> ${item.hist_days} วัน</div>
                </div>
                ${comparisonHTML}
                <div class="profile-alert-sub" style="margin-top: 5px; width: 100%; text-align: right;">บันทึกเมื่อ: ${fmtDate(item.created_at)}</div>
            </div>`;
    }).join('');
}


async function loadProfileAlerts() {
    const listEl = document.getElementById('profile-alert-list');
    if (!listEl) return;
    if (!window.isLoggedIn) { listEl.innerHTML = ''; return; }

    listEl.innerHTML = '<p class="profile-loading">กำลังโหลดรายการแจ้งเตือน...</p>';
    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/alerts/list.php`, {
            method: 'GET',
            credentials: 'include'
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) throw new Error(data.message || 'โหลดไม่สำเร็จ');
        renderProfileAlerts(data.items || []);
    } catch (err) {
        listEl.innerHTML = `<p class="profile-alert-empty" > โหลดรายการไม่สำเร็จ: ${err.message}</p> `;
    }
}

function renderProfileAlerts(items) {
    const listEl = document.getElementById('profile-alert-list');
    if (!listEl) return;
    if (!items.length) {
        listEl.innerHTML = '<p class="profile-alert-empty">ยังไม่มีรายการแจ้งเตือน<br><small>ตั้งค่าได้ที่ส่วน "แจ้งเตือนราคา" ด้านล่าง</small></p>';
        return;
    }
    const goldText = (t) => t === 'ornament' ? 'ทองรูปพรรณ' : t === 'world' ? 'ทองโลก (USD/oz)' : 'ทองคำแท่ง';
    const typeText = (t) => t === 'above' ? 'สูงกว่า หรือ เท่ากับ' : 'ต่ำกว่า หรือ เท่ากับ';
    const fmtDate = (v) => { const d = new Date(v); return isNaN(d.getTime()) ? '-' : d.toLocaleString('th-TH'); };

    listEl.innerHTML = items.map(item => {
        const target = Number(item.target_price || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 });
        const badgeClass = item.triggered ? 'profile-alert-badge done' : 'profile-alert-badge waiting';
        const badgeText = item.triggered ? 'แจ้งเตือนแล้ว' : 'รอแจ้งเตือน';
        return `
            <div class="profile-alert-item" data-alert-id="${item.id}" >
                <div class="profile-alert-info">
                    <div class="profile-alert-title">${goldText(item.gold_type)} • ${typeText(item.alert_type)} ฿${target}</div>
                    <div class="profile-alert-sub">สร้างเมื่อ ${fmtDate(item.created_at)}</div>
                </div>
                <span class="${badgeClass}">${badgeText}</span>
                <div class="profile-alert-actions">
                    <button class="profile-alert-btn-delete" onclick="deleteProfileAlert(${item.id})">ลบ</button>
                </div>
            </div> `;
    }).join('');
}

async function deleteProfileAlert(alertId) {
    if (!confirm('ต้องการลบรายการแจ้งเตือนนี้?')) return;
    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/alerts/delete.php`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: alertId })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) throw new Error(data.message || 'ลบไม่สำเร็จ');
        // รีโหลดทั้ง profile modal และ main alerts list
        loadProfileAlerts();
        loadAlertsList();
    } catch (err) {
        alert('ลบรายการไม่สำเร็จ: ' + err.message);
    }
}

async function saveProfileName() {
    const nameInput = document.getElementById('profile-name-input');
    const statusEl = document.getElementById('profile-name-status');
    const name = (nameInput?.value || '').trim();
    if (!name) {
        if (statusEl) {
            statusEl.textContent = 'กรุณากรอกชื่อ';
            statusEl.style.color = 'red';
        }
        return;
    }
    if (statusEl) {
        statusEl.textContent = 'กำลังบันทึก...';
        statusEl.style.color = '#666';
    }
    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/auth/update_profile.php`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
            throw new Error(data.message || 'ไม่สามารถบันทึกได้');
        }
        window.currentUser = { ...window.currentUser, name };
        currentUser = window.currentUser;
        localStorage.setItem('currentUser', JSON.stringify(window.currentUser));
        updateUIAfterLogin();
        if (statusEl) {
            statusEl.textContent = 'บันทึกชื่อสำเร็จ';
            statusEl.style.color = 'green';
        }
    } catch (error) {
        if (statusEl) {
            statusEl.textContent = error.message || 'เกิดข้อผิดพลาด';
            statusEl.style.color = 'red';
        }
    }
}

async function changeProfilePassword() {
    const oldInput = document.getElementById('profile-old-password');
    const newInput = document.getElementById('profile-new-password');
    const confirmInput = document.getElementById('profile-confirm-password');
    const statusEl = document.getElementById('profile-password-status');
    const oldPassword = oldInput?.value || '';
    const newPassword = newInput?.value || '';
    const confirmPassword = confirmInput?.value || '';
    if (!oldPassword || newPassword.length < 6) {
        if (statusEl) {
            statusEl.textContent = 'กรอกรหัสผ่านเดิมและรหัสใหม่อย่างน้อย 6 ตัวอักษร';
            statusEl.style.color = 'red';
        }
        return;
    }
    if (newPassword !== confirmPassword) {
        if (statusEl) {
            statusEl.textContent = 'รหัสผ่านใหม่ไม่ตรงกัน';
            statusEl.style.color = 'red';
        }
        return;
    }
    if (statusEl) {
        statusEl.textContent = 'กำลังบันทึก...';
        statusEl.style.color = '#666';
    }
    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/auth/change_password.php`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
            throw new Error(data.message || 'ไม่สามารถเปลี่ยนรหัสผ่านได้');
        }
        if (oldInput) oldInput.value = '';
        if (newInput) newInput.value = '';
        if (confirmInput) confirmInput.value = '';
        if (statusEl) {
            statusEl.textContent = 'เปลี่ยนรหัสผ่านสำเร็จ';
            statusEl.style.color = 'green';
        }
    } catch (error) {
        if (statusEl) {
            statusEl.textContent = error.message || 'เกิดข้อผิดพลาด';
            statusEl.style.color = 'red';
        }
    }
}

function forDev() {
    console.warn('forDev() is disabled in this build. Please use the login system.');
}

function checkDevLogin() {
    const devUser = sessionStorage.getItem('dev_login');
    if (devUser) {
        console.log("DEV MODE: Restoring login state from Session Storage.");
        isLoggedIn = true;
        currentUser = JSON.parse(devUser);
        window.isLoggedIn = true;
        window.currentUser = currentUser;
    }
}

async function waitForElement(selector, timeout = 6000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const el = document.querySelector(selector);
        if (el) return el;
        await new Promise(r => setTimeout(r, 100));
    }
    return null;
}

async function setupAlert() {
    if (!window.isLoggedIn) {
        showLoginModal();
        return;
    }

    const typeEl = document.getElementById('alert-type');
    const targetEl = document.getElementById('target-price');
    const emailEl = document.getElementById('user-email');
    const goldTypeEl = document.getElementById('alert-gold-type');
    const statusEl = document.getElementById('alert-status');

    const alertType = typeEl?.value || '';
    const targetPrice = parseFloat(targetEl?.value || '0');
    const email = (emailEl?.value || '').trim();
    const goldType = goldTypeEl?.value || 'bar';

    if (!alertType || !targetPrice || targetPrice <= 0 || !email) {
        if (statusEl) {
            statusEl.textContent = 'กรุณากรอกข้อมูลให้ครบถ้วน';
            statusEl.style.color = 'red';
        }
        return;
    }

    if (statusEl) {
        statusEl.textContent = 'กำลังบันทึกการแจ้งเตือน...';
        statusEl.style.color = '#666';
    }

    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/alerts/create.php`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_price: targetPrice,
                alert_type: alertType,
                gold_type: goldType,
                email: email
            })
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
            throw new Error(data.message || 'ไม่สามารถบันทึกการแจ้งเตือนได้');
        }
        if (statusEl) {
            statusEl.textContent = 'ตั้งค่าการแจ้งเตือนสำเร็จ';
            statusEl.style.color = 'green';
        }
        loadAlertsList();
    } catch (error) {
        if (statusEl) {
            statusEl.textContent = error.message || 'เกิดข้อผิดพลาดในการตั้งค่าแจ้งเตือน';
            statusEl.style.color = 'red';
        }
    }
}

function renderAlertList(items) {
    const listEl = document.getElementById('alert-list');
    if (!listEl) return;
    if (!items || items.length === 0) {
        listEl.innerHTML = `
            <div class="alert-item" >
                <div class="alert-item-meta">
                    <div class="alert-item-title">ยังไม่มีการตั้งค่าแจ้งเตือน</div>
                    <div class="alert-item-sub">ตั้งค่าใหม่ด้านบนเพื่อเริ่มใช้งาน</div>
                </div>
            </div>
            `;
        return;
    }
    const typeText = (type) => type === 'above' ? 'สูงกว่า หรือ เท่ากับ' : 'ต่ำกว่า หรือ เท่ากับ';
    const goldText = (type) => {
        if (type === 'ornament') return 'ทองรูปพรรณ';
        if (type === 'world') return 'ทองโลก (USD/oz)';
        return 'ทองคำแท่ง';
    };
    const dateText = (value) => {
        const d = new Date(value);
        return Number.isNaN(d.getTime()) ? '-' : d.toLocaleString('th-TH');
    };
    listEl.innerHTML = items.map(item => {
        const badgeClass = item.triggered ? 'alert-badge success' : 'alert-badge';
        const badgeText = item.triggered ? 'แจ้งเตือนแล้ว' : 'รอแจ้งเตือน';
        const target = Number(item.target_price || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 });
        return `
            <div class="alert-item" >
                <div class="alert-item-meta">
                    <div class="alert-item-title">${goldText(item.gold_type)} • ${typeText(item.alert_type)} ฿${target}</div>
                    <div class="alert-item-sub">สร้างเมื่อ ${dateText(item.created_at)}</div>
                </div>
                <div class="${badgeClass}">${badgeText}</div>
            </div>
            `;
    }).join('');
}

async function loadAlertsList() {
    const listEl = document.getElementById('alert-list');
    if (!listEl) return;
    if (!window.isLoggedIn) {
        listEl.innerHTML = '';
        return;
    }
    listEl.innerHTML = `
            <div class="alert-item" >
                <div class="alert-item-meta">
                    <div class="alert-item-title">กำลังโหลดรายการแจ้งเตือน...</div>
                </div>
        </div>
            `;
    try {
        const res = await fetch(`${window.APP_CONFIG.PHP_API_BASE}/alerts/list.php`, {
            method: 'GET',
            credentials: 'include'
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
            throw new Error(data.message || 'โหลดข้อมูลไม่สำเร็จ');
        }
        renderAlertList(data.items || []);
    } catch (error) {
        listEl.innerHTML = `
            <div class="alert-item">
                <div class="alert-item-meta">
                    <div class="alert-item-title">โหลดรายการไม่สำเร็จ</div>
                    <div class="alert-item-sub">${error.message || 'เกิดข้อผิดพลาด'}</div>
                </div>
            </div>
            `;
    }
}

function renderNews(articles) {
    const box = document.getElementById('techcrunch-news');
    if (!box) return;
    if (!articles || !articles.length) { box.innerHTML = '<p>ไม่สามารถโหลดข่าวได้</p>'; return; }
    const defaultImg = 'https://images.unsplash.com/photo-1610375461246-83df859d849d?w=600&q=80';
    let html = '<ul class="news-list">';
    articles.slice(0, 6).forEach(a => {
        const dateStr = a.publishedAt ? new Date(a.publishedAt).toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' }) : '';
        const imgSrc = a.urlToImage || defaultImg;
        const sourceName = typeof a.source === 'string' ? a.source : (a.source?.name || '');
        html += `<li class="news-item"><img class="news-image" src="${imgSrc}" alt="" onerror="this.src='${defaultImg}'"><div class="news-content"><a class="news-title" href="${a.url}" target="_blank" rel="noopener">${a.title || ''}</a><p class="news-description">${a.description || ''}</p><div class="news-footer"><span class="news-source">${sourceName}</span><span class="news-date">${dateStr}</span></div></div></li>`;
    });
    html += '</ul>';
    box.innerHTML = html;
}


function updateCurrentTime() {
    const allDateDisplays = document.querySelectorAll('.current-date-display');
    const allTimeDisplays = document.querySelectorAll('.current-time-display');
    const now = new Date();
    const dateString = now.toLocaleDateString('th-TH', { day: 'numeric', month: 'long', year: 'numeric' });
    const timeString = now.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    allDateDisplays.forEach(el => { el.textContent = dateString; });
    allTimeDisplays.forEach(el => { el.textContent = timeString; });
}

// Ensure the clock updates every second
if (!window.clockInterval) {
    window.clockInterval = setInterval(updateCurrentTime, 1000);
}

async function fetchAndUpdatePriceBoard() {
    const fmtTHB = (n) => (Number.isFinite(n) ? n : 0).toLocaleString('th-TH', { minimumFractionDigits: 2 });
    const toNum = (v) => {
        const n = parseFloat(String(v ?? '').replace(/,/g, ''));
        return Number.isFinite(n) ? n : null;
    };

    // --- ส่วนทองไทย (Real-time from Server) ---
    try {
        const resp = await fetch(`${window.APP_CONFIG.PYTHON_API_URL}/api/thai-gold-price`);
        if (!resp.ok) throw new Error(`Server error: ${resp.status} `);
        const data = await resp.json();

        // Normalize data
        const normalized = {
            bar_buy: toNum(data.bar_buy),
            bar_sell: toNum(data.bar_sell),
            ornament_buy: toNum(data.ornament_buy),
            ornament_sell: toNum(data.ornament_sell),
            today_change: toNum(data.today_change),
            date: data.date,
            update_round: data.update_round
        };

        if (normalized.today_change === null && Number.isFinite(latestThaiPrices?.bar_sell) && Number.isFinite(normalized.bar_sell)) {
            normalized.today_change = normalized.bar_sell - latestThaiPrices.bar_sell;
        }

        latestThaiPrices = { ...latestThaiPrices, ...normalized };

        document.getElementById('thai-bar-buy').textContent = fmtTHB(normalized.bar_buy);
        document.getElementById('thai-bar-sell').textContent = fmtTHB(normalized.bar_sell);
        document.getElementById('thai-jewelry-buy').textContent = fmtTHB(normalized.ornament_buy);
        document.getElementById('thai-jewelry-sell').textContent = fmtTHB(normalized.ornament_sell);
        document.getElementById('thai-manual-update-time').textContent = new Date().toLocaleTimeString('th-TH');

        // อัปเดตข้อมูลในแถบประกาศ
        // ถ้า date ไม่มีค่าให้ใช้ default
        let displayDate = normalized.date;
        if (!displayDate) {
            displayDate = new Date().toLocaleDateString('th-TH', {
                day: 'numeric', month: 'long', year: 'numeric'
            });
        }
        document.getElementById('thai-update-date').textContent = displayDate;
        document.getElementById('thai-update-round').textContent = normalized.update_round || 'ล่าสุด';

        const changeEl = document.getElementById('thai-today-change');
        const change = Number.isFinite(normalized.today_change) ? normalized.today_change : 0;
        if (change === 0) {
            changeEl.textContent = '- ไม่เปลี่ยนแปลง';
            changeEl.className = 'change-indicator neutral';
        } else {
            changeEl.textContent = `${change > 0 ? '▲' : '▼'} ${Math.abs(change).toLocaleString()} `;
            changeEl.className = 'change-indicator ' + (change > 0 ? 'positive' : 'negative');
        }

        // Update "last fetched" timestamp
        const fetchTime = new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const thaiTimeEl = document.getElementById('thai-manual-update-time');
        if (thaiTimeEl) thaiTimeEl.textContent = fetchTime;

    } catch (err) {
        console.error('Failed to fetch Thai gold price:', err);
        // Fallback or show error state if needed
    }

    // --- ส่วนทองโลก ---
    try {
        const wresp = await fetch(`${window.APP_CONFIG.PYTHON_API_URL}/api/world-gold-price`);
        if (!wresp.ok) throw new Error(`Server error: ${wresp.status} `);
        const wdata = await wresp.json();

        const usdPerOz = Number(wdata?.price_usd_per_ounce);
        const thbPerBaht = Number(wdata?.thb_per_baht_est);
        if (!Number.isFinite(usdPerOz) || !Number.isFinite(thbPerBaht)) {
            throw new Error('Invalid world gold payload');
        }

        document.getElementById('world-spot-usd').textContent = usdPerOz.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
        document.getElementById('world-spot-thb').textContent = thbPerBaht.toLocaleString('th-TH', { minimumFractionDigits: 2 });
        if (document.getElementById('world-update-time')) {
            document.getElementById('world-update-time').textContent = wdata.last_updated || new Date().toLocaleTimeString('th-TH');
        }
    } catch (err) {
        console.error('Failed to fetch world gold price:', err);

        // Fallback: ประมาณ Spot โลกจากราคาทองไทยล่าสุด
        const thaiSell = Number(latestThaiPrices?.bar_sell);
        const usdthbFallback = 36.85;
        const factor = (15.244 / 31.1035) * usdthbFallback;
        if (Number.isFinite(thaiSell) && thaiSell > 0 && factor > 0) {
            const usdPerOzEst = thaiSell / factor;
            const usdEl = document.getElementById('world-spot-usd');
            const thbEl = document.getElementById('world-spot-thb');
            const timeEl = document.getElementById('world-update-time');
            if (usdEl) usdEl.textContent = usdPerOzEst.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
            if (thbEl) thbEl.textContent = thaiSell.toLocaleString('th-TH', { minimumFractionDigits: 2 });
            if (timeEl) timeEl.textContent = `${new Date().toLocaleTimeString('th-TH')} (ประมาณค่า)`;
        }
    }
}
// ฟังก์ชันสำหรับสลับแท็บราคาทอง
function switchPriceTab(tabName, btn) {
    document.querySelectorAll('.price-content-wrapper').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.price-tab-link').forEach(el => el.classList.remove('active'));
    const target = document.getElementById(`${tabName}-price-content`);
    if (target) {
        target.classList.add('active');
    }
    btn.classList.add('active');
}
/* === Calculator (ต้อง login)=== */
function calculateGoldValue() {
    if (!window.isLoggedIn) return;

    const w = document.getElementById('calc-weight-input');
    const u = document.getElementById('calc-unit-select');
    if (!w || !u) return;

    const weight = parseFloat(w.value);
    if (!isFinite(weight) || weight < 0) {
        ['result-gram', 'result-baht', 'result-bar-buy', 'result-bar-sell', 'result-jewelry-buy', 'result-jewelry-sell']
            .forEach(id => { const el = document.getElementById(id); if (el) el.textContent = id.includes('result-') ? '0.00' : '0.000'; });
        return;
    }

    const GRAMS_PER_BAHT_BAR = 15.244;
    const GRAMS_PER_BAHT_ORN = 15.16;

    let bahtW_bar = 0;
    let bahtW_orn = 0;
    let grams_display = 0;

    if (u.value === 'gram') {
        bahtW_bar = weight / GRAMS_PER_BAHT_BAR;
        bahtW_orn = weight / GRAMS_PER_BAHT_ORN;
        grams_display = weight;
    } else if (u.value === 'salung') {
        bahtW_bar = weight / 4;
        bahtW_orn = weight / 4;
        grams_display = weight * (GRAMS_PER_BAHT_BAR / 4);
    } else if (u.value === 'baht') {
        bahtW_bar = weight;
        bahtW_orn = weight;
        grams_display = weight * GRAMS_PER_BAHT_BAR;
    } else if (u.value === 'kilogram') {
        bahtW_bar = (weight * 1000) / GRAMS_PER_BAHT_BAR;
        bahtW_orn = (weight * 1000) / GRAMS_PER_BAHT_ORN;
        grams_display = weight * 1000;
    }

    const fromDom = (id) => {
        const el = document.getElementById(id);
        if (!el) return null;
        let text = el.textContent || '';
        // Extract only the numbers and dots, ignoring commas and currency symbols
        text = text.replace(/,/g, '').replace(/[^\d.]/g, ''); 
        const n = parseFloat(text);
        return Number.isFinite(n) ? n : null;
    };

    const barBuy = Number.isFinite(window.latestThaiPrices?.bar_buy) ? window.latestThaiPrices.bar_buy : fromDom('thai-bar-buy');
    const barSell = Number.isFinite(window.latestThaiPrices?.bar_sell) ? window.latestThaiPrices.bar_sell : fromDom('thai-bar-sell');
    const ornBuy = Number.isFinite(window.latestThaiPrices?.ornament_buy) ? window.latestThaiPrices.ornament_buy : fromDom('thai-jewelry-buy');
    const ornSell = Number.isFinite(window.latestThaiPrices?.ornament_sell) ? window.latestThaiPrices.ornament_sell : fromDom('thai-jewelry-sell');

    if (![barBuy, barSell, ornBuy, ornSell].every(v => Number.isFinite(v))) {
        console.warn('Calculator error: Could not load active prices', { barBuy, barSell, ornBuy, ornSell });
        return;
    }

    const fmtTH = { style: 'currency', currency: 'THB', minimumFractionDigits: 2 };

    document.getElementById('result-gram').textContent = grams_display.toFixed(3);
    document.getElementById('result-baht').textContent = bahtW_bar.toFixed(3);
    document.getElementById('result-bar-buy').textContent = (bahtW_bar * barBuy).toLocaleString('th-TH', fmtTH);
    document.getElementById('result-bar-sell').textContent = (bahtW_bar * barSell).toLocaleString('th-TH', fmtTH);
    document.getElementById('result-jewelry-buy').textContent = (bahtW_orn * ornBuy).toLocaleString('th-TH', fmtTH);
    document.getElementById('result-jewelry-sell').textContent = (bahtW_orn * ornSell).toLocaleString('th-TH', fmtTH);
}
function createGoldChart(canvasId, data, label, backgroundColor, borderColor) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') {
        console.error(`Canvas or Chart.js not ready for: ${canvasId} `);
        return null;
    }

    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
        existingChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: label,
                data: data.values,
                backgroundColor: backgroundColor,
                borderColor: borderColor,
                borderWidth: 2,
                pointRadius: 1,
                fill: false,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { type: 'time', time: { unit: 'month', displayFormats: { month: 'MMM yyyy' } } },
                y: { beginAtZero: false }
            }
        }
    });
}

let liveThaiChartInstance = null;
let liveChartUpdateInterval = null;

function initLiveChartToggles() {
    const btnThai = document.getElementById('toggle-thai-chart');
    const btnWorld = document.getElementById('toggle-world-chart');
    const containerThai = document.getElementById('thai-live-container');
    const containerWorld = document.getElementById('world-live-container');

    if (!btnThai || !btnWorld || !containerThai || !containerWorld) return;

    btnThai.addEventListener('click', () => {
        btnThai.classList.add('active');
        btnWorld.classList.remove('active');
        containerThai.style.display = 'block';
        containerWorld.style.display = 'none';

        // Force redraw to prevent Chart.js stretching bug when unhiding
        if (liveThaiChartInstance) {
            liveThaiChartInstance.resize();
        }
    });

    btnWorld.addEventListener('click', () => {
        btnWorld.classList.add('active');
        btnThai.classList.remove('active');
        containerWorld.style.display = 'block';
        containerThai.style.display = 'none';
    });

    const timeBtns = document.querySelectorAll('.time-range-btn');
    timeBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            timeBtns.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const range = e.target.getAttribute('data-range');
            fetchAndRenderThaiLiveChart(range);
        });
    });
}

window.fetchAndRenderThaiLiveChart = async function (range = '1d') {
    const canvas = document.getElementById('thai-live-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    try {
        const res = await fetch(`${window.APP_CONFIG.PYTHON_API_URL}/api/intraday?range=${range}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!data.labels || !data.thai_values) throw new Error("Invalid chart data format");

        const ctx = canvas.getContext('2d');
        if (liveThaiChartInstance) {
            liveThaiChartInstance.destroy();
        }

        const datasets = [{
            label: 'ราคาทองคำไทย (Real-time)',
            data: data.thai_values,
            borderColor: '#ff9800',
            backgroundColor: 'rgba(255, 152, 0, 0.1)',
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            fill: true,
            tension: 0.1
        }];

        if (data.assoc_values && data.assoc_values.length > 0) {
            // Get the latest association price for the legend label
            const currentAssocPrice = data.assoc_values[data.assoc_values.length - 1];
            datasets.push({
                label: `ราคาสมาคมฯ (${currentAssocPrice.toLocaleString()})`,
                data: data.assoc_values,
                borderColor: '#9e9e9e',
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false,
                tension: 0.1 // Slight tension to make it look like a smooth historical line
            });
        }

        liveThaiChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB' }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { maxTicksLimit: 12 }
                    },
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });

    } catch (e) {
        console.error("Failed to fetch Thai Live Chart:", e);
    }
};

async function loadHistoricalCharts() {
    if (!document.getElementById('goldChartThai')) return;
    const days = 365;
    const generateSimpleChartData = (startVal, lowVal, highVal, endVal, volatility) => {
        const labels = [];
        const values = [];
        let price = startVal;
        const midPoint1 = Math.floor(days * 0.25);
        const midPoint2 = Math.floor(days * 0.75);
        for (let i = 0; i < days; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (days - 1 - i));
            labels.push(date);
            let trend = 0;
            if (i < midPoint1) {
                trend = (lowVal - startVal) / midPoint1;
            } else if (i < midPoint2) {
                trend = (highVal - lowVal) / (midPoint2 - midPoint1);
            } else {
                trend = (endVal - highVal) / (days - midPoint2);
            }
            price += trend;
            const noise = (Math.random() - 0.5) * volatility;
            values.push(Math.max(lowVal * 0.95, price + noise));
        }
        return { labels, values };
    };

    try {
        const resp = await fetch(`${window.APP_CONFIG.PYTHON_API_URL}/api/historical?days=${days}`);
        if (!resp.ok) throw new Error(`Server error: ${resp.status} `);
        const data = await resp.json();
        const labels = (data.labels || []).map(d => new Date(d));
        const thaiData = { labels, values: data.thai_values || [] };
        const worldData = { labels, values: data.world_values || [] };

        chartThai = createGoldChart(
            'goldChartThai',
            thaiData,
            'ราคาทองไทยย้อนหลัง (บาท)',
            'rgba(212, 175, 55, 0.2)',
            '#d4af37'
        );
        chartWorld = createGoldChart(
            'goldChartWorld',
            worldData,
            'ราคาทองโลกย้อนหลัง (USD)',
            'rgba(0, 123, 255, 0.2)',
            '#007bff'
        );
        calculateAndDisplayStats(thaiData.values, 'บาท');
    } catch (error) {
        const thaiData = generateSimpleChartData(41500, 39000, 44000, 43500, 500);
        chartThai = createGoldChart(
            'goldChartThai',
            thaiData,
            'ราคาทองไทยย้อนหลัง (บาท - ประมาณการ)',
            'rgba(212, 175, 55, 0.2)',
            '#d4af37'
        );
        const worldData = generateSimpleChartData(2380, 2346, 2626, 2600, 10);
        chartWorld = createGoldChart(
            'goldChartWorld',
            worldData,
            'ราคาทองโลกย้อนหลัง (USD - ประมาณการ)',
            'rgba(0, 123, 255, 0.2)',
            '#007bff'
        );
        calculateAndDisplayStats(thaiData.values, 'บาท');
    }
}
// == สรุปสถิติกราฟย้อนหลัง (ใช้ได้ทั้งข้อมูลเป็นตัวเลขล้วน หรือเป็นอ็อบเจ็กต์ {y: number}) ==
function calculateAndDisplayStats(arr, currency = 'บาท') {
    if (!arr || !arr.length) return;

    const vals = arr.map(v => (typeof v === 'number' ? v : (v && typeof v === 'object' ? (v.y ?? v.value ?? Number(v)) : Number(v))))
        .filter(n => Number.isFinite(n));
    if (!vals.length) return;

    const hi = Math.max(...vals);
    const lo = Math.min(...vals);
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    const ret = ((vals[vals.length - 1] - vals[0]) / vals[0]) * 100;
    const vol = (hi - lo) / avg > 0.15 ? 'สูง' : 'ปานกลาง';

    // แสดงหน่วยถูกต้อง: USD ใช้รูปแบบเงินดอลลาร์, ไทยเป็นตัวเลขปกติ (คงรูปแบบเดิมของคุณไว้)
    const fmt = currency === 'USD'
        ? { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }
        : { minimumFractionDigits: 2, maximumFractionDigits: 2 };

    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };

    set('stat-high', hi.toLocaleString('th-TH', fmt));
    set('stat-low', lo.toLocaleString('th-TH', fmt));
    set('stat-avg', avg.toLocaleString('th-TH', fmt));

    const elRet = document.getElementById('stat-return');
    if (elRet) {
        elRet.textContent = `${ret.toFixed(2)}% `;
        elRet.className = 'stat-value ' + (ret >= 0 ? 'positive' : 'negative');
    }
    set('stat-volatility', vol);
}
function openHistoryChart(which) {
    const thaiBox = document.getElementById('thai-history-chart');
    const worldBox = document.getElementById('world-history-chart');
    const thaiBtn = document.querySelector('.history-toggle[onclick*="thai"]');
    const worldBtn = document.querySelector('.history-toggle[onclick*="world"]');
    if (!thaiBox || !worldBox) return;

    if (which === 'thai') {
        thaiBox.style.display = 'block'; worldBox.style.display = 'none';
        if (thaiBtn) thaiBtn.classList.add('active');
        if (worldBtn) worldBtn.classList.remove('active');
        if (chartThai) calculateAndDisplayStats(chartThai.data.datasets[0].data, 'บาท');
    } else {
        thaiBox.style.display = 'none'; worldBox.style.display = 'block';
        if (thaiBtn) thaiBtn.classList.remove('active');
        if (worldBtn) worldBtn.classList.add('active');
        if (chartWorld) calculateAndDisplayStats(chartWorld.data.datasets[0].data, 'USD');
    }
}
function getLiveUsdThb() {
    // 1) ถ้ามีเก็บไว้ตอนอัปเดตราคาโลก/กระดาน
    if (window.latestFx && Number.isFinite(window.latestFx.USDTHB)) {
        return window.latestFx.USDTHB;
    }
    // 2) ถ้ามีแสดงใน DOM เช่น <span id="world-usdthb">33.72</span>
    const el = document.getElementById('world-usdthb');
    if (el) {
        const v = parseFloat(String(el.textContent).replace(/,/g, ''));
        if (!Number.isNaN(v)) return v;
    }
    // 3) fallback ค่ากลางปัจจุบัน
    return 36.50;
}
async function fetchGoldNews() {
    const box = document.getElementById('techcrunch-news');
    if (!box) return;
    box.textContent = 'กำลังโหลดข่าวสารล่าสุด...';

    // Point to the Python backend which handles Thai news and fallbacks
    const url = `${window.APP_CONFIG.PYTHON_API_URL}/api/news`;

    try {
        const r = await fetch(url);
        if (!r.ok) throw new Error(r.statusText);
        const j = await r.json();

        // The Python backend returns an array of articles directly or throws a 500 error
        if (Array.isArray(j)) {
             renderNews(j);
        } else {
             throw new Error("Invalid news format received from server");
        }

    } catch (e) {
        console.error('News error:', e);
        box.innerHTML = `<p>เกิดข้อผิดพลาดในการโหลดข่าว</p>`;
    }
}
/* ==========  วาดกราฟพยากรณ์ (ARIMA + Confidence Band) ========== */
function renderForecastChart(payload) {
    const el = document.getElementById('forecast-chart');
    if (!el || typeof Chart === 'undefined') return;
    const isMobile = window.innerWidth < 768;

    const labels = payload.labels.map(d => new Date(d));
    const histLen = payload.history.length;
    const forecastLen = payload.forecast.length;
    const totalLen = labels.length;

    // Build history line data — padded at start, null at end
    const histPad = Array(totalLen - histLen).fill(null);
    const histData = histPad.concat(payload.history);

    // Build forecast data — overlap last real point for continuity
    const lastRealPrice = payload.history[histLen - 1];
    const forecastData = new Array(totalLen).fill(null);
    forecastData[totalLen - forecastLen - 1] = lastRealPrice;  // overlap point
    for (let i = 0; i < forecastLen; i++) {
        forecastData[totalLen - forecastLen + i] = payload.forecast[i];
    }

    // Build confidence band data (upper/lower)
    const upperData = new Array(totalLen).fill(null);
    const lowerData = new Array(totalLen).fill(null);
    if (payload.upper_bound && payload.lower_bound) {
        for (let i = 0; i < forecastLen; i++) {
            upperData[totalLen - forecastLen + i] = payload.upper_bound[i];
            lowerData[totalLen - forecastLen + i] = payload.lower_bound[i];
        }
    }

    const datasets = [
        {
            label: 'ราคาจริง (ย้อนหลัง)',
            data: histData,
            borderColor: '#999',
            backgroundColor: 'rgba(0,0,0,0)',
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.1
        },
        {
            label: `คาดการณ์ (${payload.model || 'AI'})`,
            data: forecastData,
            borderColor: '#d4af37',
            backgroundColor: 'rgba(212,175,55,0.15)',
            borderWidth: 2.5,
            pointRadius: 0,
            borderDash: [6, 4],
            tension: 0.15
        },
        {
            label: 'ขอบบน (90% CI)',
            data: upperData,
            borderColor: 'rgba(212,175,55,0.4)',
            backgroundColor: 'rgba(0,0,0,0)',
            borderWidth: 1,
            borderDash: [3, 3],
            pointRadius: 0,
            fill: false,
            tension: 0.15
        },
        {
            label: 'ขอบล่าง (90% CI)',
            data: lowerData,
            borderColor: 'rgba(212,175,55,0.4)',
            backgroundColor: 'rgba(212,175,55,0.08)',
            borderWidth: 1,
            borderDash: [3, 3],
            pointRadius: 0,
            fill: '-1',  // Fill between this and the previous dataset (upper)
            tension: 0.15
        }
    ];

    const ctx = el.getContext('2d');
    if (window.forecastChart && typeof window.forecastChart.destroy === 'function') window.forecastChart.destroy();
    window.forecastChart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: isMobile ? 'day' : 'day' },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: isMobile ? 6 : 10,
                        maxRotation: 0,
                        font: { size: isMobile ? 10 : 12 }
                    }
                },
                y: {
                    beginAtZero: false,
                    ticks: {
                        font: { size: isMobile ? 10 : 12 }
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: isMobile ? 12 : 18,
                        boxHeight: isMobile ? 8 : 10,
                        usePointStyle: false,
                        font: { size: isMobile ? 10 : 12 }
                    }
                },
                tooltip: {
                    bodyFont: { size: isMobile ? 11 : 12 },
                    titleFont: { size: isMobile ? 11 : 12 },
                    callbacks: {
                        label: function(ctx) {
                            const v = ctx.parsed.y;
                            if (v == null) return null;
                            return `${ctx.dataset.label}: ฿${Number(v).toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
                        }
                    }
                }
            }
        }
    });

    // Update summary display
    const fmt = v => Number(v).toLocaleString('th-TH', { minimumFractionDigits: 2 });
    document.getElementById('trend-indicator')?.replaceChildren(document.createTextNode(payload.summary.trend));
    document.getElementById('max-price')?.replaceChildren(document.createTextNode(`฿${fmt(payload.summary.max)} `));
    document.getElementById('min-price')?.replaceChildren(document.createTextNode(`฿${fmt(payload.summary.min)} `));
    document.getElementById('confidence-level')?.replaceChildren(document.createTextNode(`${payload.summary.confidence}% `));
}
/* ==========  ตัวเรียก API พยากรณ์ ========== */
async function generateForecast() {
    if (!window.isLoggedIn) {
        showLoginModal();
        return;
    }

    const btn = document.getElementById('generate-forecast');
    const resultsContainer = document.getElementById('forecast-results');
    if (!btn || !resultsContainer) return;

    btn.textContent = 'กำลังคำนวณ...';
    btn.disabled = true;
    resultsContainer.style.display = 'none';

    const periodEl = document.getElementById('forecast-period');
    const histDaysEl = document.getElementById('forecast-hist-days');
    if (!periodEl || !histDaysEl) return;

    const period = parseInt(periodEl.value || '7', 10);
    const histDays = histDaysEl.value || '90';
    const model = 'ml-linear'; // บังคับใช้ AI Predictive ตัวเดียวที่เสถียรสุด

    const trendEl = document.getElementById('trend-indicator');
    if (trendEl) trendEl.textContent = 'กำลังคำนวณ...';

    try {
        const url = `${window.APP_CONFIG.PYTHON_API_URL}/api/forecast?period=${period}&model=${model}&hist_days=${histDays}`;

        const r = await fetch(url);
        const j = await r.json();
        if (!r.ok) throw new Error(j?.error || r.statusText);

        const payload = j;

        renderForecastChart(payload);

        // [เพิ่ม] อัปเดตข้อมูลสรุปเพิ่มเติม
        document.getElementById('hist-days-display').textContent = histDays;
        document.getElementById('model-used-display').textContent = payload.model || 'N/A';
        document.getElementById('data-source-display').textContent = payload.summary.source || 'N/A';
        const trendDisplay = document.getElementById('trend-indicator');
        if (trendDisplay) trendDisplay.textContent = payload.summary.trend || '--';
        const maxDisplay = document.getElementById('max-price');
        if (maxDisplay) maxDisplay.textContent = payload.summary.max ? Number(payload.summary.max).toLocaleString() : '--';
        const minDisplay = document.getElementById('min-price');
        if (minDisplay) minDisplay.textContent = payload.summary.min ? Number(payload.summary.min).toLocaleString() : '--';
        const confidenceDisplay = document.getElementById('confidence-level');
        if (confidenceDisplay) confidenceDisplay.textContent = payload.summary.confidence ? `${payload.summary.confidence}% ` : '--';

        window.latestForecastData = {
            target_date: payload.labels[payload.labels.length - 1],
            trend: payload.summary.trend,
            max_price: payload.summary.max,
            min_price: payload.summary.min,
            confidence: payload.summary.confidence,
            hist_days: histDays
        };

        const btnSaveForecast = document.getElementById('save-forecast-btn');
        if (btnSaveForecast) {
            btnSaveForecast.style.display = 'inline-block';
            document.getElementById('save-forecast-status').textContent = '';
            btnSaveForecast.disabled = false;
            btnSaveForecast.innerHTML = '<i class="fas fa-save"></i> บันทึกคำพยากรณ์';
        }

        resultsContainer.style.display = 'grid';

    } catch (e) {
        console.error('Forecast error:', e);
        alert('Error 1: ' + e.message + '\n' + e.stack);
    } finally {
        btn.textContent = 'สร้างการพยากรณ์';
        btn.disabled = false;
    }
}


/* =========================================================
   IN-APP NOTIFICATIONS (BELL ICON)
   ========================================================= */
async function fetchNotifications() {
    if (!window.isLoggedIn) return;
    try {
        const r = await fetch('api/api/notifications/list.php');
        const j = await r.json();
        if (j.success) {
            updateNotifBadge(j.unread_count);
            renderNotifications(j.data);
        }
    } catch (e) {
        console.error('Error fetching notifications:', e);
    }
}

function updateNotifBadge(count) {
    const badge = document.getElementById('notif-count');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.add('show');
    } else {
        badge.classList.remove('show');
    }
}

function renderNotifications(notifs) {
    const container = document.getElementById('notif-list-container');
    if (!container) return;
    
    if (!notifs || notifs.length === 0) {
        container.innerHTML = '<p class="notif-empty">ไม่มีการแจ้งเตือนใหม่</p>';
        return;
    }

    container.innerHTML = notifs.map(n => `
        <a href="${n.link || '#'}" class="notif-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}">
            <div class="notif-icon ${n.type}">
                <i class="fas ${getNotifIcon(n.type)}"></i>
            </div>
            <div class="notif-content">
                <div class="notif-title">${n.title}</div>
                <div class="notif-message">${n.message}</div>
                <div class="notif-time">${formatTimeAgo(n.created_at)}</div>
            </div>
        </a>
    `).join('');

    // ผูก event กดแจ้งเตือน
    container.querySelectorAll('.notif-item').forEach(el => {
        el.addEventListener('click', async (e) => {
            const id = el.getAttribute('data-id');
            await markNotifRead(id);
        });
    });
}

function getNotifIcon(type) {
    switch (type) {
        case 'price_alert': return 'fa-bell';
        case 'forecast_result': return 'fa-chart-line';
        default: return 'fa-info-circle';
    }
}

function formatTimeAgo(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffMin < 1) return 'เมื่อครู่นี้';
    if (diffMin < 60) return `${diffMin} นาทีที่แล้ว`;
    if (diffHour < 24) return `${diffHour} ชั่วโมงที่แล้ว`;
    if (diffDay < 7) return `${diffDay} วันที่แล้ว`;
    return date.toLocaleDateString('th-TH');
}

async function markNotifRead(id) {
    try {
        await fetch('api/api/notifications/mark_read.php', {
            method: 'POST',
            body: JSON.stringify({ id })
        });
        fetchNotifications();
    } catch (e) {
        console.error('Error marking notification read:', e);
    }
}

/* =========================================================
   LINE MESSAGING API INTEGRATION
   ========================================================= */
async function loadLineStatus() {
    const connectContainer = document.getElementById('line-connect-container');
    const statusContainer = document.getElementById('line-connected-status');
    const userNameDisplay = document.getElementById('line-user-name');
    
    if (!window.currentUser) return;
    
    // จำลองการเช็คสถานะจากข้อมูล User (ปกติควรมี API เช็ค)
    if (window.currentUser.line_user_id) {
        if (connectContainer) connectContainer.style.display = 'none';
        if (statusContainer) statusContainer.style.display = 'block';
        if (userNameDisplay) userNameDisplay.textContent = `LINE User: ${window.currentUser.line_display_name || 'เชื่อมต่อแล้ว'}`;
    } else {
        if (connectContainer) connectContainer.style.display = 'block';
        if (statusContainer) statusContainer.style.display = 'none';
    }
}

// ผูก Event ปุ่มเชื่อมต่อ LINE
document.getElementById('line-connect-btn')?.addEventListener('click', async () => {
    try {
        const r = await fetch('api/api/profile/generate_line_code.php', { method: 'POST' });
        const j = await r.json();
        if (j.success) {
            const code = j.code;
            const botId = '@your_bot_id'; // ต้องเปลี่ยนเป็น LINE Bot ID ของคุณจริง
            const qrUrl = `https://line.me/R/ti/p/${botId}`;
            
            alert(`วิธีเชื่อมต่อ LINE:\n1. เพิ่มเพื่อนกับบอททองของเรา\n2. ส่งข้อความคำว่า: LINK-${code}\n\nระบบจะทำการเชื่อมต่อบัญชีให้ทันทีครับ!`);
            
            // เปลี่ยนข้อความปุ่มเพื่อแสดงรหัส
            const btn = document.getElementById('line-connect-btn');
            if (btn) {
                btn.innerHTML = `<i class="fab fa-line"></i> ส่งรหัส LINK-${code} ไปที่ LINE`;
            }
        }
    } catch (e) {
        console.error('Error generating LINE code:', e);
    }
});

async function saveLineId(lineId, displayName) {
    try {
        const r = await fetch('api/api/profile/update_line.php', {
            method: 'POST',
            body: JSON.stringify({ line_user_id: lineId, display_name: displayName })
        });
        const j = await r.json();
        if (j.success) {
            window.currentUser.line_user_id = lineId;
            window.currentUser.line_display_name = displayName;
            saveUserToStorage(window.currentUser);
            loadLineStatus();
        }
    } catch (e) {
        console.error('Error saving LINE ID:', e);
    }
}

/* =========================================================
   WEB PUSH NOTIFICATIONS
   ========================================================= */
async function initWebPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    
    try {
        const registration = await navigator.serviceWorker.register('sw.js');
        console.log('Service Worker registered');
        
        if (window.isLoggedIn) {
            checkPushSubscription(registration);
        }
    } catch (e) {
        console.error('Service Worker registration failed:', e);
    }
}

async function checkPushSubscription(registration) {
    const subscription = await registration.pushManager.getSubscription();
    const connectContainer = document.getElementById('push-connect-container');
    const statusContainer = document.getElementById('push-status-container');
    
    if (!subscription) {
        console.log('User not subscribed to push yet');
        if (connectContainer) connectContainer.style.display = 'block';
        if (statusContainer) statusContainer.style.display = 'none';
    } else {
        console.log('User is subscribed to push');
        if (connectContainer) connectContainer.style.display = 'none';
        if (statusContainer) statusContainer.style.display = 'block';
        savePushSubscription(subscription);
    }
}

async function loadPushStatus() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    const registration = await navigator.serviceWorker.getRegistration();
    if (registration) {
        checkPushSubscription(registration);
    }
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function getVapidPublicKey() {
    try {
        const res = await fetch(`${window.APP_CONFIG.PYTHON_API_URL}/api/web-push/public-key`);
        const data = await res.json().catch(() => ({}));
        if (res.ok && data && data.public_key) return data.public_key;
    } catch (e) { }
    return null;
}

// ผูกปุ่มสมัคร Push
document.getElementById('push-subscribe-btn')?.addEventListener('click', async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        alert('บราวเซอร์ของคุณไม่รองรับ Web Push');
        return;
    }

    try {
        const registration = await navigator.serviceWorker.getRegistration();
        if (!registration) {
            alert('Service Worker ยังไม่พร้อมใช้งาน กรุณาลองใหม่');
            return;
        }

        // ขอสิทธิ์
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            alert('กรุณาอนุญาตการแจ้งเตือนในบราวเซอร์ของคุณ');
            return;
        }

        const publicKey = await getVapidPublicKey();
        if (!publicKey) {
            alert('ยังไม่ได้ตั้งค่า VAPID_PUBLIC_KEY บนเซิร์ฟเวอร์');
            return;
        }

        // สมัคร (Subscribe)
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicKey)
        });

        savePushSubscription(subscription);
        loadPushStatus();
        alert('เปิดใช้งานการแจ้งเตือนสำเร็จ!');
    } catch (e) {
        console.error('Push subscribe error:', e);
        alert('เกิดข้อผิดพลาดในการเปิดใช้งาน: ' + e.message);
    }
});

// ผูกปุ่มยกเลิก Push
document.getElementById('push-unsubscribe-btn')?.addEventListener('click', async () => {
    const registration = await navigator.serviceWorker.getRegistration();
    const subscription = await registration.pushManager.getSubscription();
    if (subscription) {
        await subscription.unsubscribe();
        // แจ้ง Server ให้ลบ Subscription
        await fetch('api/api/profile/update_push.php', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(null)
        });
        loadPushStatus();
        alert('ปิดการแจ้งเตือนเรียบร้อยแล้ว');
    }
});

async function savePushSubscription(subscription) {
    try {
        await fetch('api/api/profile/update_push.php', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(subscription)
        });
    } catch (e) {
        console.error('Error saving push subscription:', e);
    }
}

/* ====  Initialize ==== */
async function initializeApp() {
    checkDevLogin();
    console.log('🚀 Initializing app...');
    loadUserFromStorage();
    updateUIAfterLogin();
    checkSession();
    
    // [เพิ่ม] ระบบ Web Push Notification
    initWebPush();

    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    // ปุ่ม "ข้อมูลส่วนตัว" - เปิด Profile Modal (ต้องผูกก่อน await เพื่อให้ใช้ได้ทันที)
    const profileLink = document.getElementById('profileLink');
    if (profileLink) {
        profileLink.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            document.getElementById('user-menu-container')?.classList.remove('show');
            showProfileModal();
        });
    }

    // ปุ่มบันทึกใน Profile Modal
    document.getElementById('profile-save-name')?.addEventListener('click', saveProfileName);

    // [เพิ่ม] ปุ่มแจ้งเตือน (Bell Icon)
    const notifBtn = document.getElementById('notifBtn');
    const notifDropdown = document.getElementById('notifDropdown');
    if (notifBtn && notifDropdown) {
        notifBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            notifDropdown.classList.toggle('show');
            if (notifDropdown.classList.contains('show')) {
                fetchNotifications();
            }
        });

        // ปิด dropdown เมื่อคลิกที่อื่น
        document.addEventListener('click', () => {
            notifDropdown.classList.remove('show');
        });
        notifDropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    // [เพิ่ม] ปุ่ม "อ่านทั้งหมด"
    document.getElementById('mark-all-read')?.addEventListener('click', async () => {
        await markNotifRead('all');
    });
    document.getElementById('profile-save-password')?.addEventListener('click', changeProfilePassword);

    // [OPTIMIZATION] Don't await the price board fetch so it doesn't block the rest of the page (like charts loading)
    fetchAndUpdatePriceBoard().catch(err => console.error('Price board error:', err));
    setInterval(fetchAndUpdatePriceBoard, 30000); // ราคาทองวันนี้: ทุก 30 วินาที
    
    // [เพิ่ม] อัปเดตการแจ้งเตือน In-App ทุก 1 นาที
    setInterval(() => {
        if (window.isLoggedIn) fetchNotifications();
    }, 60000);

    // --- ข่าว: โหลดครั้งแรก + auto-refresh ทุก 10 นาที ---
    fetchGoldNews().catch(err => console.error('News error:', err));
    setInterval(() => {
        console.log('🔄 Auto-refreshing news...');
        fetchGoldNews().catch(err => console.error('News refresh error:', err));
    }, 600000); // 10 นาที


    const tvDiv = document.getElementById('tradingview_full_chart');
    if (tvDiv && typeof TradingView !== 'undefined') {
        new TradingView.widget({
            autosize: true, symbol: 'OANDA:XAUUSD', interval: '15', timezone: 'Asia/Bangkok', theme: 'light', style: '1',
            locale: 'th', enable_publishing: false, hide_side_toolbar: true, withdateranges: true, hide_volume: true,
            studies: ['MASimple@tv-basicstudies'], container_id: 'tradingview_full_chart'
        });
    }

    initLiveChartToggles();

    setTimeout(() => {
        if (typeof Chart !== 'undefined') {
            // --- กราฟย้อนหลัง: โหลดครั้งแรก + auto-refresh ทุก 30 นาที ---
            loadHistoricalCharts();
            setInterval(() => {
                console.log('🔄 Auto-refreshing historical charts...');
                loadHistoricalCharts();
            }, 1800000); // 30 นาที

            // --- กราฟ real-time: โหลดครั้งแรก + auto-refresh ทุก 60 วินาที ---
            fetchAndRenderThaiLiveChart();
            if (liveChartUpdateInterval) clearInterval(liveChartUpdateInterval);
            liveChartUpdateInterval = setInterval(() => {
                console.log('🔄 Auto-refreshing live chart...');
                fetchAndRenderThaiLiveChart();
            }, 60000); // 1 นาที (เดิม 5 นาที)
        }
    }, 500);



    const btnForecast = await waitForElement('#generate-forecast');
    if (btnForecast) {
        btnForecast.addEventListener('click', generateForecast);
    }

    document.getElementById('save-forecast-btn')?.addEventListener('click', saveForecast);

    document.getElementById('loginBtn')?.addEventListener('click', (e) => {
        e.preventDefault();
        showLoginModal();
    });

    const loginModal = document.getElementById('loginModal');
    if (loginModal) {
        loginModal.addEventListener('click', hideLoginModal);
        loginModal.querySelector('.modal-container')?.addEventListener('click', (e) => e.stopPropagation());
    }


    document.getElementById('signUpInline')?.addEventListener('click', () => setAuthMode('register'));
    document.getElementById('signInInline')?.addEventListener('click', () => setAuthMode('login'));

    document.getElementById('login-button')?.addEventListener('click', login);
    document.getElementById('register-button')?.addEventListener('click', register);
    document.getElementById('logoutBtn')?.addEventListener('click', (e) => { e.preventDefault(); logout(); });
    document.getElementById('forgot-password-link')?.addEventListener('click', (e) => {
        e.preventDefault();
        setAuthMode('forgot');
    });
    document.getElementById('backToLogin')?.addEventListener('click', (e) => {
        e.preventDefault();
        setAuthMode('login');
    });
    document.getElementById('forgot-submit')?.addEventListener('click', submitForgotPassword);
    setupPasswordToggles();

    console.log('✅ App initialized');

    // จัดการ User Dropdown Menu
    const userBtn = document.getElementById('userBtn');
    if (userBtn) {
        userBtn.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();
            const parent = userBtn.closest('.nav-item-dropdown');
            parent?.classList.toggle('show');
        });
    }

    window.addEventListener('click', function (event) {
        const userMenuContainer = document.getElementById('user-menu-container');
        if (userMenuContainer && !userMenuContainer.contains(event.target)) {
            userMenuContainer.classList.remove('show');
        }
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    const navbar = document.querySelector('.navbar');
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('primaryNav');

    function closeMobileNav() {
        navbar?.classList.remove('nav-open');
        document.body.classList.remove('nav-open');
        navToggle?.setAttribute('aria-expanded', 'false');
    }

    navToggle?.addEventListener('click', () => {
        const isOpen = navbar?.classList.toggle('nav-open');
        document.body.classList.toggle('nav-open', Boolean(isOpen));
        navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    navMenu?.querySelectorAll('a').forEach((link) => {
        if (link.id === 'userBtn' || link.id === 'notifBtn') return;
        if (link.closest('.nav-item-dropdown')) return;
        link.addEventListener('click', closeMobileNav);
    });

    document.querySelectorAll('.mobile-quick-nav a').forEach((link) => {
        link.addEventListener('click', closeMobileNav);
    });

    document.getElementById('quickAccountBtn')?.addEventListener('click', () => {
        closeMobileNav();
        if (window.isLoggedIn) {
            showProfileModal();
        } else {
            showLoginModal();
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) closeMobileNav();
    });

    window.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeMobileNav();
            hideLoginModal();
        }
    });

    await loadAllComponents();
    await initializeApp();
});
